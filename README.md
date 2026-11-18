# ⚽ FUTBora - Addon de Futebol para Stremio & Nuvio

Addon completo que adiciona os **jogos de futebol do dia** ao catálogo do **Stremio** e **Nuvio**, funcionando exatamente como o **Cinemeta**, mas dedicado ao futebol nacional e internacional.

---

## 🌟 Recursos

- **Catálogo Integrado**: Aparece na tela inicial ("Descobrir" / "Catálogo") do Stremio e Nuvio.
- **Foco no Futebol**:
  - 🇧🇷 Brasileirão Série A & Série B
  - 🇧🇷 Copa do Brasil
  - 🌎 Copa Libertadores & Sul-Americana
  - 🇪🇸 La Liga (Espanha)
  - 🇬🇧 Premier League (Inglaterra)
  - 🏆 UEFA Champions League & Europa League
  - 🇮🇹 Serie A (Itália)
  - 🇩🇪 Bundesliga (Alemanha)
- **Informações em Tempo Real**:
  - Placar atualizado e minuto de jogo (ex: `2ºT - 72'`).
  - Distintivos e logos oficiais dos clubes.
  - Horário de Brasília (`Hoje às 21:30`).
  - Estádio / Local do confronto.
  - Informações de transmissão oficial (Globo, Premiere, ESPN, CazéTV, Star+, etc.).
- **Pôsteres Dinâmicos (SVG)**: Gera pôsteres elegantes estilo card de confronto para cada partida diretamente no Stremio.
- **Zero Dependências Externas**: Feito em Python nativo puro, sem necessidade de `pip install`.

---

## 🚀 Como Rodar Localmente

### Opção 1: Windows (1 Clique)
Basta dar dois cliques no arquivo:
```cmd
run.bat
```

### Opção 2: Terminal / Prompt de Comando
```bash
python server.py
```

O servidor iniciará em `http://localhost:7000`.

---

## 📲 Como Instalar no Stremio e Nuvio

1. Com o servidor rodando, abra o **Stremio** ou **Nuvio**.
2. Vá na aba **Addons** (ícone de peça de quebra-cabeça).
3. Na barra de pesquisa ou no campo **"Adicionar Addon / URL do Manifest"**, cole:
   ```text
   http://localhost:7000/manifest.json
   ```
4. Clique em **Instalar**.
5. Vá para a aba **Descobrir** (Catálogo) -> Selecione o catálogo **"⚽ Jogos de Hoje (Futebol)"**.

---

## ☁️ Hospedagem 24/7 Gratuita (Para Celular, TV e Web)

Para usar no celular, Chromecast ou TV sem depender do PC ligado:
1. Suba esta pasta para um repositório no GitHub.
2. Conecte ao **Render.com** (usando o `Dockerfile` ou `render.yaml`) ou **Railway.app**.
3. O serviço gerará uma URL como:
   `https://futbora-stremio.onrender.com/manifest.json`
4. Instale essa URL no Stremio/Nuvio em qualquer dispositivo!
