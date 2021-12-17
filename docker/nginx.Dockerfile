FROM nginx
RUN rm /etc/nginx/conf.d/default.conf
COPY docker/nginx.conf /etc/nginx/conf.d
COPY backend/static /usr/share/nginx/static
EXPOSE 80
