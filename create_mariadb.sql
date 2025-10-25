-- create_mariadb.sql
-- Script para criar a estrutura do banco de dados no MariaDB

-- Apaga as tabelas se elas já existirem, para permitir a recriação limpa
DROP TABLE IF EXISTS `arquivos_licitacao`;
DROP TABLE IF EXISTS `itens_licitacao`;
DROP TABLE IF EXISTS `licitacoes`;

-- Tabela Principal: licitacoes
CREATE TABLE `licitacoes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `numeroControlePNCP` VARCHAR(255) UNIQUE NOT NULL,
    `numeroCompra` VARCHAR(255),
    `anoCompra` INT,
    `processo` VARCHAR(255),
    `tipolnstrumentoConvocatorioId` INT,
    `tipolnstrumentoConvocatorioNome` VARCHAR(255),
    `modalidadeId` INT,
    `modalidadeNome` VARCHAR(255),
    `modoDisputaId` INT,
    `modoDisputaNome` VARCHAR(255),
    `situacaoCompraId` INT,
    `situacaoCompraNome` VARCHAR(255),
    `objetoCompra` TEXT,
    `informacaoComplementar` TEXT,
    `srp` BOOLEAN,
    `amparoLegalCodigo` INT,
    `amparoLegalNome` VARCHAR(255),
    `amparoLegalDescricao` TEXT,
    `valorTotalEstimado` DECIMAL(15, 2),
    `valorTotalHomologado` DECIMAL(15, 2),
    `dataAberturaProposta` DATETIME,
    `dataEncerramentoProposta` DATETIME,
    `dataPublicacaoPncp` DATE,
    `dataInclusao` DATE,
    `dataAtualizacao` DATE,
    `sequencialCompra` INT,
    `orgaoEntidadeCnpj` VARCHAR(14),
    `orgaoEntidadeRazaoSocial` VARCHAR(255),
    `orgaoEntidadePoderId` VARCHAR(10),
    `orgaoEntidadeEsferaId` VARCHAR(10),
    `unidadeOrgaoCodigo` VARCHAR(30),
    `unidadeOrgaoNome` VARCHAR(255),
    `unidadeOrgaoCodigoIbge` INT,
    `unidadeOrgaoMunicipioNome` VARCHAR(255),
    `unidadeOrgaoUfSigla` VARCHAR(2),
    `unidadeOrgaoUfNome` VARCHAR(255),
    `usuarioNome` VARCHAR(255),
    `linkSistemaOrigem` TEXT,
    `link_portal_pncp` TEXT,
    `justificativaPresencial` TEXT,
    `situacaoReal` VARCHAR(100),
    INDEX `idx_data_atualizacao` (`dataAtualizacao`),
    INDEX `idx_uf_sigla` (`unidadeOrgaoUfSigla`),
    INDEX `idx_modalidade_id` (`modalidadeId`)
    FULLTEXT KEY `idx_fts_busca` (`objetoCompra`, `orgaoEntidadeRazaoSocial`, `unidadeOrgaoNome`, `numeroControlePNCP`, `unidadeOrgaoMunicipioNome`, `unidadeOrgaoUfNome`, `orgaoEntidadeCnpj`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Itens
CREATE TABLE `itens_licitacao` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `licitacao_id` INT NOT NULL,
    `numeroItem` VARCHAR(20),
    `descricao` TEXT,
    `materialOuServicoNome` VARCHAR(100),
    `quantidade` DECIMAL(15, 4),
    `unidadeMedida` VARCHAR(150),
    `valorUnitarioEstimado` DECIMAL(15, 4),
    `valorTotal` DECIMAL(15, 2),
    `orcamentoSigiloso` BOOLEAN,
    `itemCategoriaNome` VARCHAR(255),
    `categoriaItemCatalogo` VARCHAR(255),
    `criterioJulgamentoNome` VARCHAR(255),
    `situacaoCompraItemNome` VARCHAR(255),
    `tipoBeneficioNome` VARCHAR(255),
    `incentivoProdutivoBasico` BOOLEAN,
    `dataInclusao` DATE,
    `dataAtualizacao` DATE,
    `temResultado` BOOLEAN,
    `informacaoComplementar` TEXT,
    FOREIGN KEY (`licitacao_id`) REFERENCES `licitacoes`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Arquivos
CREATE TABLE `arquivos_licitacao` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `licitacao_id` INT NOT NULL,
    `titulo` VARCHAR(255),
    `link_download` VARCHAR(512) UNIQUE,
    `dataPublicacaoPncp` DATE,
    `anoCompra` INT,
    `statusAtivo` BOOLEAN,
    FOREIGN KEY (`licitacao_id`) REFERENCES `licitacoes`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- TABELAS PARA O BLOG E USUARIOS
-- =============================================

DROP TABLE IF EXISTS `posts`;
DROP TABLE IF EXISTS `usuarios`;
DROP TABLE IF EXISTS `posts_tags`; -- Apaga a de junção primeiro
DROP TABLE IF EXISTS `categorias`;
DROP TABLE IF EXISTS `tags`;

-- Tabela de Usuários para o Admin
CREATE TABLE `usuarios` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(80) UNIQUE NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `is_admin` BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Categorias (Cada post tem UMA categoria)
CREATE TABLE `categorias` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nome` VARCHAR(100) UNIQUE NOT NULL,
    `slug` VARCHAR(100) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Tags (Um post pode ter VÁRIAS tags)
CREATE TABLE `tags` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nome` VARCHAR(100) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Posts do Blog - MODIFICADA
CREATE TABLE `posts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `titulo` VARCHAR(255) NOT NULL,
    `slug` VARCHAR(255) UNIQUE NOT NULL,
    `resumo` TEXT,
    `conteudo_completo` LONGTEXT,
    `imagem_destaque` VARCHAR(255),
    `data_publicacao` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `autor_id` INT,
    `categoria_id` INT,
    `is_featured` BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (`autor_id`) REFERENCES `usuarios`(`id`),
    FOREIGN KEY (`categoria_id`) REFERENCES `categorias`(`id`) ON DELETE SET NULL -- << NOVA CHAVE ESTRANGEIRA
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- ON DELETE SET NULL: Se uma categoria for deletada, os posts dela ficam sem categoria (NULL).

-- Tabela de Junção Posts <-> Tags
CREATE TABLE `posts_tags` (
    `post_id` INT NOT NULL,
    `tag_id` INT NOT NULL,
    PRIMARY KEY (`post_id`, `tag_id`),
    FOREIGN KEY (`post_id`) REFERENCES `posts`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`tag_id`) REFERENCES `tags`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- ON DELETE CASCADE: Se um post ou tag for deletado, a associação entre eles é deletada automaticamente.