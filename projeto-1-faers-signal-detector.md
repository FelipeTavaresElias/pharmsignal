# Projeto 1 — PharmSignal: Detector de Sinais de Farmacovigilância (FAERS)

> **One-liner:** App web onde você digita um medicamento e ele mostra quais eventos adversos estão desproporcionalmente reportados na base pública da FDA, usando as métricas reais da indústria (PRR/ROR).

**Por que este projeto existe (narrativa de portfólio):** prova que você domina o conceito técnico central de pharmacovigilance — *disproportionality analysis* — antes de qualquer empregador pedir. É o projeto que um recrutador de CRO abre e pensa "esse candidato já fala a língua". Prioridade nº 1 do portfólio.

**Público-alvo do repo:** recrutadores e hiring managers de PV (internacionais) → **README e UI em inglês.** Este documento de gestão fica em português.

---

## Decisões de arquitetura (Senior Dev)

| Decisão | Escolha | Por quê |
|---|---|---|
| Fonte de dados | **openFDA API** (`api.fda.gov/drug/event.json`) | Evita baixar os arquivos brutos do FAERS (gigabytes, parsing complexo). A API devolve contagens prontas. Simples > completo. |
| Métricas | **PRR e ROR com IC 95%** | São as duas métricas clássicas de sinal. Fórmulas fecham em ~30 linhas de código. |
| Stack | **Python + pandas + Streamlit** | Um arquivo, deploy grátis no Streamlit Community Cloud, zero frontend custom. |
| Cache | `st.cache_data` (TTL 24h) | openFDA tem rate limit (240 req/min sem key; com key gratuita, 120k/dia). |
| O que NÃO fazer | Sem banco de dados, sem login, sem docker | MVP de portfólio. Cada complexidade a mais atrasa o deploy e não impressiona ninguém. |

**Lógica central (para você entender antes de codar):** para um par droga-evento, monta-se a tabela de contingência 2×2 — (a) relatos com a droga E o evento, (b) droga sem o evento, (c) evento sem a droga, (d) nem um nem outro. `PRR = [a/(a+b)] / [c/(c+d)]`. `ROR = (a/b)/(c/d)`. Sinal clássico: PRR ≥ 2, chi² ≥ 4, a ≥ 3. A openFDA fornece a, a+b, a+c e o total via 4 queries de contagem.

---

## Fases (importar no Linear como Milestones)

### 🏁 Fase 0 — Setup & Prova de Conceito `v0.1` (est. 1 sessão de ~3h)

- [ ] **P0** Criar repo `pharmsignal` no GitHub com `.gitignore` Python e licença MIT
- [ ] **P0** Obter API key gratuita da openFDA e guardar em `.env` (nunca commitar)
- [ ] **P0** Script `poc.py`: dado um nome de droga fixo (ex.: `"metformin"`), buscar via API os 20 eventos adversos mais reportados (`count=patient.reaction.reactionmeddrapt.exact`)
- [ ] **P0** Validar no console que os números batem com uma busca manual no site do openFDA
- **Critério de aceite da fase:** rodar `python poc.py` imprime uma tabela droga→eventos com contagens reais.

### ⚙️ Fase 1 — Motor de Sinal `v0.5` (est. 1–2 sessões)

- [ ] **P0** Função `contingency(drug, event)` → devolve a, b, c, d via 4 chamadas de contagem à API
- [ ] **P0** Funções `prr(a,b,c,d)` e `ror(a,b,c,d)` com intervalo de confiança 95% (fórmula log-normal padrão)
- [ ] **P0** Função `detect_signals(drug, top_n=20)`: para cada evento do top N da droga, calcula PRR/ROR e marca `signal=True` se PRR ≥ 2 e a ≥ 3
- [ ] **P1** Testes unitários das fórmulas com um caso calculado à mão (planilha de conferência no repo)
- [ ] **P1** Tratamento de erros: droga não encontrada, API fora, contagem zero (evitar divisão por zero com correção de Haldane +0.5)
- **Critério de aceite:** `detect_signals("amiodarone")` devolve DataFrame com colunas `event, a, PRR, PRR_CI, ROR, ROR_CI, signal` e resultados clinicamente plausíveis (ex.: distúrbios tireoidianos aparecem).

### 🖥️ Fase 2 — Interface & MVP público `v1.0` (est. 1–2 sessões)

- [ ] **P0** `app.py` em Streamlit: campo de busca de droga, tabela de resultados ordenada por PRR, badges vermelhos nos sinais
- [ ] **P0** Gráfico de barras horizontal dos 10 maiores PRRs (matplotlib ou nativo do Streamlit)
- [ ] **P0** Disclaimer visível: *"Signals are statistical, not causal. Educational tool using public FDA data."* (isso é maturidade profissional — avaliadores notam)
- [ ] **P0** Deploy no Streamlit Community Cloud com secrets configurados
- [ ] **P1** Spinner de loading + cache de 24h por droga
- **Critério de aceite:** link público funciona no celular; busca por 3 drogas diferentes responde em < 15s cada.

### 📣 Fase 3 — Polimento de portfólio `v1.1` (est. 1 sessão)

- [ ] **P0** README em inglês: problema em 3 frases → screenshot → link ao vivo → como funciona (metodologia PRR/ROR com as fórmulas) → limitações honestas (reporting bias do FAERS, sem denominador de exposição)
- [ ] **P1** Comparação lado a lado de 2 drogas (tabs no Streamlit)
- [ ] **P1** Botão "Download CSV" dos resultados
- [ ] **P2** Post curto no LinkedIn (em inglês) apresentando o projeto — marca o início da sua presença em "clinical AI/PV"
- **Critério de aceite:** uma pessoa leiga entende o que o app faz em 30 segundos só pelo README.

---

## Definition of Done (projeto inteiro)
1. Link público funcionando + repo com README em inglês e screenshot.
2. Fórmulas com teste unitário e planilha de conferência.
3. Disclaimer regulatório visível.
4. Você consegue explicar PRR vs ROR em 60 segundos de entrevista (escreva essa explicação no README — vira seu roteiro).

## Riscos & linhas de corte
- **Risco:** rate limit da API em demo ao vivo → **Mitigação:** cache + 3 drogas pré-carregadas como exemplos clicáveis.
- **Se o tempo apertar, corte nesta ordem:** comparação de drogas → download CSV → gráfico. **Nunca corte:** as fórmulas corretas e o disclaimer.

## Talking points de entrevista (anote no Linear como issue "Prep")
- "Escolhi a openFDA API em vez dos dumps brutos do FAERS: trade-off consciente de completude por simplicidade e tempo de entrega."
- "PRR ≥ 2 com a ≥ 3 é screening, não causalidade — o passo seguinte na indústria seria avaliação médica caso a caso." ← esta frase demonstra que você entende o fluxo real de PV.
