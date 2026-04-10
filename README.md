# NEOREPLAY - Bot Discord

Bot Discord para gerenciar licenças NEOREPLAY.

## Setup Local

```bash
pip install -r requirements.txt
python main.py
```

## Variáveis de Ambiente

Configure em `.env`:
- `DISCORD_TOKEN` - Token do Bot Discord
- `DONO_ID` - ID do dono do bot (seu ID)
- `SERVIDOR_URL` - URL do Site (ex: https://neoreplay.onrender.com)
- `API_SECRET` - Token secreto (deve ser o mesmo do Site)

## Comandos do Bot

- `!gerar` - Gera nova licença
- `!listar [filtro]` - Lista licenças
- `!info <key>` - Detalhes da licença
- `!banir <key>` - Banir licença
- `!reativar <key>` - Reativar licença
- `!resetar <key>` - Resetar HWID
- `!remover <key>` - Remover licença
- `!ajuda` - Mostra ajuda
- `!status` - Status do servidor

## Deploy na Discloud

1. Upload do repositório GitHub
2. Configurar variáveis de ambiente
3. Deploy!
