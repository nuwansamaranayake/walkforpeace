FROM node:20-alpine AS build
WORKDIR /app/frontend
RUN echo '{"private":true,"workspaces":["shared","www"]}' > package.json
COPY frontend/shared/ ./shared/
COPY frontend/www/ ./www/
RUN npm install
RUN npm run build --workspace=@walkforpeace/www
FROM alpine:3.19
COPY --from=build /app/frontend/www/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'WWW frontend deployed'"]
