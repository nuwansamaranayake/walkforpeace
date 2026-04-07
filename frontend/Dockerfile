FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM alpine:3.19
RUN apk add --no-cache coreutils
COPY --from=build /app/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Frontend deployed to /app/dist'; ls -la /app/dist/"]
