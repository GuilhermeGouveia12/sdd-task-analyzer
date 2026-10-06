# CONTEXT_RULES.md

Regras de governança de contexto para qualquer assistente de IA (ex.: Gemini, ChatGPT, GitHub Copilot, Claude) utilizado na geração ou manutenção de código deste repositório. Este arquivo é a fonte de contexto persistente transposta da especificação SDD da Fase 1 (`specs/task_analyzer_spec.md`).

## 1. Diretrizes Arquiteturais (Obrigatórias)

- Utilizar Python 3.11+ como versão mínima obrigatória.
- Utilizar type hints (anotações de tipo) em 100% das funções e parâmetros.
- Seguir o princípio Single Responsibility (SRP) e as convenções de código limpo do PEP 8.
- Documentação formal no padrão Google style docstrings para módulos, classes, funções e parâmetros.
- Funções devem ser pequenas, coesas e com um único propósito.
- Tratamento de exceções específico, com classes de exceção próprias (`TaskValidationError`) e mensagens claras.
- Logs estruturados utilizando o módulo padrão `logging` (nunca `print`).
- Prevenção explícita de divisão por zero em qualquer cálculo de média/percentual.

## 2. Proibições Explícitas (Regras Restritivas)

- Não utilizar bibliotecas externas não autorizadas (apenas biblioteca padrão do Python; `pytest` é autorizado exclusivamente para testes).
- Não alterar, remover ou adaptar os cenários de teste fornecidos na especificação.
- Não modificar a estrutura de pastas definida neste repositório.
- Não persistir dados em arquivos ou bancos de dados — o módulo opera inteiramente em memória.
- Não alterar a assinatura (nome e parâmetros) das funções públicas (`analyze_tasks`) sem autorização explícita.
- Não gerar código sem os testes automatizados correspondentes para novas funcionalidades.
- Não inserir código duplicado ou desnecessário (evitar over-engineering).
- Não assumir comportamentos não especificados no contrato de negócio — qualquer ambiguidade deve ser levada de volta ao revisor humano.

## 3. Regras de Interação com Agentes de IA

- Sempre fornecer à IA o contexto completo (este arquivo + `specs/task_analyzer_spec.md`) antes de solicitar geração de código.
- Validar, antes de aceitar qualquer sugestão, que a IA compreendeu corretamente o contrato de negócio e as restrições apresentadas.
- Solicitar explicações do raciocínio da IA sempre que houver dúvida sobre a solução proposta.
- Revisar criticamente todo o código gerado antes de qualquer commit — nunca aceitar sugestões de forma automática.
- Rejeitar e solicitar nova geração para qualquer resposta que viole as proibições explícitas ou o contrato definido na especificação.

## 4. Plano de Homologação Humana

Todo código gerado por IA é submetido ao seguinte processo antes de ser aceito e versionado:

1. Execução completa da suíte de testes automatizados (`pytest`) para validação funcional.
2. Revisão de conformidade com o contrato de negócio e com estas regras (CONTEXT_RULES).
3. Análise de qualidade de código: legibilidade, tratamento de erros, aderência ao PEP 8.
4. Testes manuais complementares em casos de borda não cobertos automaticamente.
5. Somente após aprovação em todas as etapas anteriores, o código é commitado e enviado via Pull Request para revisão.

> No SDD, a especificação é o contrato e o código-fonte da verdade. A IA é a executora. O desenvolvedor é o arquiteto de especificações e o homologador crítico do que for gerado.
