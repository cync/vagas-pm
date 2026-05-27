# Vagas PM Internacional

🌐 **Acesse o site:** [https://cync.github.io/vagas-pm/](https://cync.github.io/vagas-pm/)

Site de vagas internacionais para Product Manager — atualizado automaticamente via Cowork.

Organizado por data (ano / mês / execução), com filtros por plataforma ATS e busca por empresa/cargo.

## Como funciona

- A tarefa agendada **VagasPM** roda diariamente e busca novas vagas em ATS internacionais (Lever, Ashby, Greenhouse, SmartRecruiters, We Work Remotely, entre outros)
- O resultado é salvo em `vagas_pm_YYYY-MM-DD.md` na pasta `VagasInternacionais`
- O script `generate_site.py` lê todos os arquivos `.md` e gera o `index.html` atualizado
- A tarefa agendada **VagasPM-GitPush** faz o push para o GitHub Pages automaticamente logo depois

## Repositório

[github.com/cync/vagas-pm](https://github.com/cync/vagas-pm)
