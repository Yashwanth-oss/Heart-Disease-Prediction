# Frontend Static Production Server
FROM nginx:alpine

# Copy static frontend assets to Nginx html directory
COPY . /usr/share/nginx/html

# Expose standard HTTP port
EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
