# Sistema de Gestão de Auditoria Interna - FUSVE

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)

## 📋 Sobre o Projeto

O **Sistema de Gestão de Auditoria Interna** é uma aplicação web desenvolvida para a **Fundação de Ensino Superior de Vassouras (FUSVE)** com o objetivo de automatizar e organizar o processo de auditoria interna, seguindo as melhores práticas e normas de auditoria.

O sistema permite o gerenciamento completo do ciclo de auditoria, desde o planejamento até a comunicação dos resultados, passando pelo mapeamento de processos, identificação de riscos e avaliação de controles internos.

---

## 🎯 Funcionalidades Principais

### 📅 Planejamento
- **Plano Anual de Auditoria**: Visualização e download do plano anual em PDF
- **Auditorias Trimestrais**: Criação e gestão de auditorias por trimestre e área

### 🔍 Execução (Mapeamento)
- **Cadastro de Áreas e Funcionários**: Gestão das unidades organizacionais e seus colaboradores
- **Diagnóstico de Processos**:
  - Cadastro de novos processos com informações detalhadas
  - Edição de processos existentes
  - Identificação de riscos associados
  - Definição de executores e responsáveis
- **Detalhamento de Auditorias**:
  - Visualização de processos selecionados por auditoria
  - Edição in-place de processos dentro da auditoria
  - Gestão de riscos por etapa
  - Cadastro de controles mitigadores

### 📊 Comunicação dos Resultados
- **Visão Geral dos Processos**: Dashboard com todos os processos mapeados, com filtros por área e auditoria
- **Geração de Relatórios**: Exportação de relatórios em PDF com detalhes dos processos e riscos

---

## 🏗️ Arquitetura do Projeto
GERADOR DE DADOS/
├── app.py # Ponto de entrada principal
├── database.py # Conexão com banco de dados
├── logic.py # Camada de acesso aos dados
│
├── modules/ # Módulos organizados por fase
│ ├── auth/ # Autenticação e sessão
│ │ └── login.py
│ │
│ ├── shared/ # Componentes compartilhados
│ │ ├── utils.py # Funções utilitárias
│ │ ├── components.py # Componentes visuais
│ │ └── validators.py # Validações
│ │
│ ├── planejamento/ # Fase 1: Planejamento
│ │ └── plano_anual.py
│ │
│ ├── execucao/ # Fase 2: Execução (Mapeamento)
│ │ ├── areas.py # Cadastro de áreas e funcionários
│ │ ├── processos.py # Diagnóstico de processos
│ │ ├── auditorias.py # Detalhamento de auditorias
│ │ └── visao_geral.py # Visão geral dos processos
│ │
│ └── comunicacaoresultados/ # Fase 3: Comunicação dos Resultados
│ ├── relatorios.py # Geração de relatórios
│ ├── checklists.py # (em desenvolvimento)
│ └── pareceres.py # (em desenvolvimento)
│
├── assets/ # Imagens e arquivos estáticos
└── utils/ # Utilitários gerais


---

## 🗄️ Modelo de Dados

O sistema utiliza um banco de dados PostgreSQL hospedado no Supabase
