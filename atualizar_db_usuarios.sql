-- =======================================================
-- 1. Tabelas de Usuários e Auth (Estrutura Base)
-- =======================================================

CREATE TABLE IF NOT EXISTS `usuarios_status` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `uid_externo` VARCHAR(128) UNIQUE NOT NULL, -- Firebase UID
    `email` VARCHAR(255),
    `nome` VARCHAR(255),
    `is_pro` BOOLEAN DEFAULT FALSE,
    `status_assinatura` ENUM('free', 'trial', 'active', 'canceled', 'expired', 'billing_issue', 'grace_period') DEFAULT 'free',
    `data_expiracao_atual` DATETIME DEFAULT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_uid` (`uid_externo`),
    INDEX `idx_status_pro` (`is_pro`, `status_assinatura`) -- Índice composto para o Worker voar
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `usuarios_dispositivos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `tipo` ENUM('mobile_android', 'mobile_ios', 'web_browser') NOT NULL,
    `token_push` VARCHAR(512) NOT NULL,
    `device_info` JSON, -- Mudamos para JSON para flexibilidade futura
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_user_token` (`usuario_id`, `token_push`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =======================================================
-- 2. Sistema de Alertas (NORMALIZADO - A Ferrari)
-- =======================================================

-- Tabela Pai (O "Cabeçalho" do alerta)
CREATE TABLE IF NOT EXISTS `preferencias_alertas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `nome_alerta` VARCHAR(100),
    `enviar_push` BOOLEAN DEFAULT TRUE,
    `enviar_email` BOOLEAN DEFAULT FALSE,
    `ativo` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE,
    INDEX `idx_alerta_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabelas Filhas (Aqui mora a performance)

CREATE TABLE IF NOT EXISTS `alertas_ufs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `alerta_id` INT NOT NULL,
    `uf` CHAR(2) NOT NULL, -- Ex: BA, SP
    FOREIGN KEY (`alerta_id`) REFERENCES `preferencias_alertas`(`id`) ON DELETE CASCADE,
    INDEX `idx_uf` (`uf`) -- Fundamental para a busca reversa
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `alertas_municipios` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `alerta_id` INT NOT NULL,
    `municipio_nome` VARCHAR(255) NOT NULL,
    FOREIGN KEY (`alerta_id`) REFERENCES `preferencias_alertas`(`id`) ON DELETE CASCADE,
    INDEX `idx_municipio` (`municipio_nome`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `alertas_modalidades` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `alerta_id` INT NOT NULL,
    `modalidade_id` INT NOT NULL,
    FOREIGN KEY (`alerta_id`) REFERENCES `preferencias_alertas`(`id`) ON DELETE CASCADE,
    INDEX `idx_modalidade` (`modalidade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `alertas_termos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `alerta_id` INT NOT NULL,
    `termo` VARCHAR(255) NOT NULL,
    `tipo` ENUM('INCLUSAO', 'EXCLUSAO') NOT NULL,
    FOREIGN KEY (`alerta_id`) REFERENCES `preferencias_alertas`(`id`) ON DELETE CASCADE,
    INDEX `idx_termo` (`termo`) -- Ajuda a encontrar quem quer "trator"
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =======================================================
-- 3. Tabelas Auxiliares (Pagamento e Favoritos)
-- =======================================================

CREATE TABLE IF NOT EXISTS `assinaturas_historico` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT,
    `uid_externo` VARCHAR(128),
    `evento` VARCHAR(50),
    `produto_id` VARCHAR(100),
    `event_id` VARCHAR(100) UNIQUE, -- Garante idempotência
    `entitlement_id` VARCHAR(100),
    `data_compra` DATETIME,
    `data_expiracao` DATETIME,
    `json_original` JSON,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `usuarios_licitacoes_favoritas` (
    `usuario_id` INT NOT NULL,
    `licitacao_pncp` VARCHAR(50) NOT NULL,
    `adicionado_em` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`usuario_id`, `licitacao_pncp`),
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `usuarios_filtros_salvos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `id_mobile` VARCHAR(100) NOT NULL,
    `nome_filtro` VARCHAR(100) NOT NULL,
    `configuracao_json` JSON NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_user_filter` (`usuario_id`, `id_mobile`),
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =======================================================
-- 4. Otimização na Tabela Principal (Licitacoes)
-- =======================================================
-- Se a tabela licitacoes já existe, rodamos isso. Se não, crie ela com FULLTEXT.
-- Isso é CRUCIAL para a busca rápida de texto.

ALTER TABLE `licitacoes` ADD COLUMN IF NOT EXISTS `notificacao_processada` TINYINT DEFAULT 0;
CREATE INDEX IF NOT EXISTS `idx_notificacao_status` ON `licitacoes` (`notificacao_processada`);
-- Adiciona coluna para controlar o tempo de travamento
ALTER TABLE `licitacoes` ADD COLUMN `processamento_inicio` DATETIME DEFAULT NULL;
-- (Opcional) Index para deixar a faxina rápida
CREATE INDEX `idx_zumbi_check` ON `licitacoes` (`notificacao_processada`, `processamento_inicio`);

-- Cria índice FULLTEXT para buscas turbinadas (Opcional se seu MariaDB for muito antigo, mas recomendado)
-- ATENÇÃO: Só roda se a tabela for InnoDB ou MyISAM
-- CREATE FULLTEXT INDEX ft_objeto ON licitacoes(objetoCompra); 
-- (Descomente a linha acima se quiser criar agora, ou deixe o app criar)