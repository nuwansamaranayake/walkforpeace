FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package.json
COPY frontend/shared/ frontend/shared/
COPY frontend/register/ frontend/register/
WORKDIR /app/frontend
RUN npm install --workspace=@walkforpeace/register
RUN npm run build --workspace=@walkforpeace/register

FROM alpine:3.19
RUN apk add --no-cache coreutils
COPY --from=build /app/frontend/register/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Register frontend deployed'; ls -la /app/dist/"]
