-- ATUALIZAR TABELAS EXISTENTES OU CRIAR NOVAS

-- 1. Flag de controle na tabela PRINCIPAL de licitações
ALTER TABLE `licitacoes` ADD COLUMN IF NOT EXISTS `notificacao_processada` BOOLEAN DEFAULT 0;
CREATE INDEX IF NOT EXISTS `idx_notificacao_pendente` ON `licitacoes` (`notificacao_processada`);

-- 2. Tabela de Usuários (Status de Assinatura)
CREATE TABLE IF NOT EXISTS `usuarios_status` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `uid_externo` VARCHAR(128) UNIQUE NOT NULL,
    `email` VARCHAR(255),
    `nome` VARCHAR(255),
    `is_pro` BOOLEAN DEFAULT FALSE,
    `status_assinatura` ENUM('free', 'trial', 'active', 'canceled', 'expired') DEFAULT 'free',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_uid` (`uid_externo`), -- Rápido para login
    INDEX `idx_is_pro` (`is_pro`)    -- Rápido para filtrar quem recebe
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Dispositivos (Tokens FCM)
CREATE TABLE IF NOT EXISTS `usuarios_dispositivos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `tipo` ENUM('mobile_android', 'mobile_ios', 'web_browser') NOT NULL,
    `token_push` VARCHAR(512) NOT NULL,
    `device_info` VARCHAR(255),
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_user_token` (`usuario_id`, `token_push`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Preferências de alertas (Agora suportando MULTI seleção)
CREATE TABLE IF NOT EXISTS `preferencias_alertas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `usuario_id` INT NOT NULL,
    `nome_alerta` VARCHAR(100),    
    `uf` TEXT,          
    `municipio` TEXT,
    `modalidades` TEXT,    
    `termos_inclusao` TEXT,
    `termos_exclusao` TEXT,
    `apenas_status_recebendo` BOOLEAN DEFAULT TRUE,    
    `enviar_push` BOOLEAN DEFAULT TRUE,
    `enviar_email` BOOLEAN DEFAULT FALSE,
    `ativo` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE
    INDEX `idx_alerta_ativo` (`ativo`), 
    INDEX `idx_usuario_alerta` (`usuario_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Tabelas auxiliares do seu app (Favoritos e Filtros Salvos)
CREATE TABLE IF NOT EXISTS `usuarios_Licitacoes_favoritas` (
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
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_user_filter` (`usuario_id`, `id_mobile`),
    FOREIGN KEY (`usuario_id`) REFERENCES `usuarios_status`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- LIMPEZA DE SEGURANÇA (Se já rodou antes):
UPDATE `licitacoes` SET `notificacao_processada` = 1 WHERE `notificacao_processada` = 0;