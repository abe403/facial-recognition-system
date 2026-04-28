# Stage 1: Build the Angular application
FROM node:20-bookworm-slim AS build-step

WORKDIR /app

# Copy package files and install dependencies
COPY package.json ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve the application with Nginx
FROM nginx:stable-alpine

# Copy the build output to Nginx's html directory
COPY --from=build-step /app/dist/facegym/browser /usr/share/nginx/html

# Copy custom nginx config to handle SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
