FROM nginx
COPY docker/nginx.template /etc/nginx/templates/default.conf.template
COPY backend/static /usr/share/nginx/static
EXPOSE 80
