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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tabela de Itens
CREATE TABLE `itens_licitacao` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `licitacao_id` INT NOT NULL,
    `numeroItem` VARCHAR(20),
    `descricao` TEXT,
    `materialOuServicoNome` VARCHAR(100),
    `quantidade` DECIMAL(15, 4),
    `unidadeMedida` VARCHAR(50),
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