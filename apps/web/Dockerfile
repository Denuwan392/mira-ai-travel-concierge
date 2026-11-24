FROM node:22-bookworm-slim
WORKDIR /app
ARG MIRA_COMPASS_URL=http://compass:5175
ENV MIRA_COMPASS_URL=$MIRA_COMPASS_URL
ARG MIRA_API_URL
ENV MIRA_API_URL=$MIRA_API_URL NEXT_TELEMETRY_DISABLED=1 COPILOTKIT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY app ./app
COPY lib ./lib
COPY public ./public
COPY next.config.ts tsconfig.json ./
RUN npm run build
CMD ["node_modules/.bin/next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
