# Build stage
FROM node:18-alpine as build
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Build the application
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80
EXPOSE 3000

# Overwrite default nginx config to route traffic on 3000 as well and handle SPA routing
RUN echo 'server { \
    listen 3000; \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
