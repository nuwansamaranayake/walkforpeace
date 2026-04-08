FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/www/ ./
RUN npm install
RUN npm run build

FROM alpine:3.19
COPY --from=build /app/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'WWW frontend deployed'"]
