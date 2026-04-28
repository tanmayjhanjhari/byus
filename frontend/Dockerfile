# Stage 1: Build
FROM node:20-alpine as build-stage

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# Build the app
# Note: VITE_API_URL should be provided as a build arg or handled at runtime
# For Cloud Run, build-time args are easiest for the static bundle
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy built assets
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Cloud Run defaults to 8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
