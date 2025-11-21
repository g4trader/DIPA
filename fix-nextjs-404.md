# 🔧 Como corrigir erros 404 do Next.js

Os arquivos estáticos existem no disco, mas o servidor não está servindo corretamente.

## Solução rápida:

### 1. Pare o servidor Next.js atual
Pressione `Ctrl+C` no terminal onde o Next.js está rodando.

### 2. Limpe o cache do Next.js
```bash
rm -rf .next
```

### 3. Reinicie o servidor
```bash
npm run dev
```

---

## Se o problema persistir:

### Opção 1: Limpar completamente e reconstruir
```bash
# Pare o servidor (Ctrl+C)

# Limpe tudo
rm -rf .next
rm -rf node_modules/.cache

# Reinicie
npm run dev
```

### Opção 2: Verificar se há outro processo na porta 3000
```bash
lsof -ti:3000 | xargs kill -9
npm run dev
```

### Opção 3: Rebuild completo
```bash
# Pare o servidor
# Limpe
rm -rf .next

# Build completo
npm run build

# Inicie em modo dev
npm run dev
```

---

## Verificação:

Após reiniciar, verifique:
1. O servidor inicia sem erros
2. Os arquivos aparecem corretamente no navegador
3. Não há mais erros 404 no console





