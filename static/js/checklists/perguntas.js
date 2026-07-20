export const PERGUNTAS = {
    governanca: [
        {
            id: 1,
            pergunta: "O fluxo das etapas e seus objetivos são de fato realizados?",
            ordem: 1,
            precisaEvidencia: true,
            temSubitens: true,
            subitens: [
                {
                    id: '1.1',
                    texto: "Verificando se o que foi feito até agora, segue o padrão relatado no mapeamento?"
                },
                {
                    id: '1.2',
                    texto: "Solicite execuções feitas e compare com o mapeamento. Está cumprindo o que diz fazer?"
                }
            ],
            compartilhaComentario: true,
            compartilhaEvidencia: true
        },
        {
            id: 2,
            pergunta: "Fazendo simulações, compare com o mapeamento. Está cumprindo o que diz fazer?",
            ordem: 2,
            precisaEvidencia: false
        },
        { 
            id: 3, 
            pergunta: "Existem procedimentos operacionais padronizados (POPs) documentados e atualizados para os processos-chave da área?", 
            ordem: 3, 
            precisaEvidencia: false 
        },
        { 
            id: 4, 
            pergunta: "Os proprietários dos processos e as responsabilidades por resultados e riscos são claramente definidos, conhecidos e aceitos na área?", 
            ordem: 4, 
            precisaEvidencia: false 
        },
        { 
            id: 5, 
            pergunta: "As decisões operacionais são tomadas no nível hierárquico correto (evitando escalonamentos desnecessários ou decisões tomadas por pessoas sem alçada)?", 
            ordem: 5, 
            precisaEvidencia: false 
        },
        { 
            id: 6, 
            pergunta: "A gestão da área realiza monitoramento contínuo dos processos?", 
            ordem: 6, 
            precisaEvidencia: false 
        },
        { 
            id: 7, 
            pergunta: "Os dados e relatórios operacionais reportados à gestão são confiáveis, precisos e utilizados para a tomada de decisão?", 
            ordem: 7, 
            precisaEvidencia: false 
        },
        { 
            id: 8, 
            pergunta: "Os indicadores de desempenho (KPIs) da área estão alinhados com os objetivos estratégicos da empresa?", 
            ordem: 8, 
            precisaEvidencia: false 
        },
        { 
            id: 9, 
            pergunta: "Os problemas operacionais e as não conformidades são comunicados à gestão superior no tempo adequado?", 
            ordem: 9, 
            precisaEvidencia: false 
        },
        { 
            id: 10, 
            pergunta: "A área realiza revisões periódicas do seu próprio desempenho, identificando e implementando melhorias nos processos?", 
            ordem: 10, 
            precisaEvidencia: false 
        },
        { 
            id: 11, 
            pergunta: "Os recursos (pessoas, tecnologia) alocados para a área são suficientes e adequados para o cumprimento dos objetivos operacionais?", 
            ordem: 11, 
            precisaEvidencia: false 
        },
        { 
            id: 12, 
            pergunta: "A área demonstra comprometimento ético no dia a dia, aderindo a políticas e reportando desvios sem medo de retaliação?", 
            ordem: 12, 
            precisaEvidencia: false 
        },
        { 
            id: 13, 
            pergunta: "O Auditado validou por email se existe mapeamento de processos feito pela área escritório de processos?", 
            ordem: 13, 
            precisaEvidencia: true 
        }
    ],
    riscos: [
        { id: 1, pergunta: "Validar se os Riscos e Fator de Riscos estão coerentes com o Objetivo da etapa.", ordem: 1, precisaEvidencia: false },
        { id: 2, pergunta: "Verificar se os riscos estão atualizados e sendo monitorados pelo gestor de primeira linha.", ordem: 2, precisaEvidencia: false },
        { id: 3, pergunta: "A área realiza mapeamento de riscos dos seus processos operacionais regularmente (ex: anualmente ou após mudanças significativas)?", ordem: 3, precisaEvidencia: false },
        { id: 4, pergunta: "Os riscos chave (ex: erro humano, falha de sistema, fraude) estão claramente identificados e documentados pela própria área?", ordem: 4, precisaEvidencia: false },
        { id: 5, pergunta: "A análise de riscos inclui a avaliação da probabilidade de ocorrência e do impacto financeiro/reputacional/operacional?", ordem: 5, precisaEvidencia: false },
        { id: 6, pergunta: "Existe um plano de ação formalizado para mitigar os riscos classificados como Alto ou Crítico?", ordem: 6, precisaEvidencia: false },
        { id: 7, pergunta: "Os controles internos da área foram especificamente desenhados para reduzir os riscos identificados (e não apenas herdados de outros processos)?", ordem: 7, precisaEvidencia: false },
        { id: 8, pergunta: "A área possui e testa planos de contingência/continuidade de negócios (plano B) para a não interrupção de processos que possuem maiores riscos?", ordem: 8, precisaEvidencia: false },
        { id: 9, pergunta: "A área monitora indicadores-chave de risco (KRIs) que sinalizam o aumento da exposição aos riscos operacionais?", ordem: 9, precisaEvidencia: false },
        { id: 10, pergunta: "Os eventos de perda ou incidentes operacionais são registrados, analisados e utilizados para ajustar a avaliação de risco da área?", ordem: 10, precisaEvidencia: false },
        { id: 11, pergunta: "O Gerente da Área (Primeira Linha de Defesa) revisa e confirma o status dos principais riscos operacionais da sua área periodicamente?", ordem: 11, precisaEvidencia: false },
        { id: 12, pergunta: "O Auditado validou por email se existe mapeamento de RISCO feito pela área Gerência de riscos e Compliance?", ordem: 12, precisaEvidencia: true },
    ],
    controles: [
        { id: 1, pergunta: "Testar se a Ação dos Controles de fato mitigam os Fatores de Riscos informados na matriz de riscos. Verificando se o que foi feito até agora, segue o padrão relatado no mapeamento? Solicite execuções feitas e compare com o mapeamento. Está cumprindo o que diz fazer?", ordem: 1, precisaEvidencia: true },
        { id: 2, pergunta: "Testar se a Ação dos Controles de fato mitigam os Fatores de Riscos informados na matriz de riscos. Fazendo simulações, comparando com o mapeamento. Está cumprindo o que diz fazer?", ordem: 2, precisaEvidencia: true },
        { id: 3, pergunta: "Os controles são preventivos (impedem o erro) sempre que possível, ao invés de apenas detectivos (identificam o erro após a ocorrência)?", ordem: 3, precisaEvidencia: false },
        { id: 4, pergunta: "Existe segregação de funções adequada dentro dos processos operacionais (ex: quem aprova não é quem executa, quem registra não é quem concilia)?", ordem: 4, precisaEvidencia: false },
        { id: 5, pergunta: "Os controles automáticos (configurações do sistema) são revisados e testados após atualizações ou mudanças no sistema?", ordem: 5, precisaEvidencia: false },
        { id: 6, pergunta: "O passo do controle (ex: revisão, aprovação, conciliação) é realizado na frequência exigida e sem exceções não autorizadas?", ordem: 6, precisaEvidencia: false },
        { id: 7, pergunta: "O responsável pelo controle deixa evidência clara (assinatura, log do sistema, captura de tela) de que o controle foi executado e revisado?", ordem: 7, precisaEvidencia: false },
        { id: 8, pergunta: "Os controles-chave são executados por pessoas com o conhecimento e a autoridade necessários para tal?", ordem: 8, precisaEvidencia: false },
        { id: 9, pergunta: "As falhas ou exceções encontradas nos controles são escaladas imediatamente para tratamento e correção?", ordem: 9, precisaEvidencia: false },
        { id: 10, pergunta: "A área rastreia e monitora as ações corretivas implementadas para remediar as deficiências de controle identificadas?", ordem: 10, precisaEvidencia: false },
        { id: 11, pergunta: "As reconciliações (ex: contábeis, estoques) são realizadas, e os itens pendentes são investigados e resolvidos prontamente?", ordem: 11, precisaEvidencia: false },
        { id: 12, pergunta: "O Auditado validou por email se existe mapeamento de CONTROLE feito pela área Gerência de riscos e Compliance?", ordem: 12, precisaEvidencia: true },
    ]
};