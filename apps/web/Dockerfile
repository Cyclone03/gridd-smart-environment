# Image de production du frontend GRIDD.
#
# Étape 1 : installation reproductible (npm ci) et compilation Vite + serveur.
# Étape 2 : image d'exécution minimale (Node LTS, utilisateur non privilégié)
#           contenant uniquement dist/ (fichiers statiques) et dist-server/.
#
# L'adresse de l'API n'est PAS intégrée à l'image : elle est lue au démarrage
# (GRIDD_API_URL) et servie au navigateur via /env.js.

ARG NODE_VERSION=22

# ---------- Construction ----------
FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---------- Exécution ----------
FROM node:${NODE_VERSION}-alpine AS runtime
ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0
WORKDIR /app

# Le serveur n'a aucune dépendance npm : seuls les fichiers compilés sont copiés.
COPY --from=build --chown=node:node /app/package.json ./package.json
COPY --from=build --chown=node:node /app/dist ./dist
COPY --from=build --chown=node:node /app/dist-server ./dist-server

# Utilisateur non privilégié fourni par l'image officielle Node.
USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist-server/index.js"]
