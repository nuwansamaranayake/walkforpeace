FROM node:20-alpine AS build
WORKDIR /app/frontend

# Create workspace root that only knows about shared + register
RUN echo '{"private":true,"workspaces":["shared","register"]}' > package.json
COPY frontend/shared/ ./shared/
COPY frontend/register/ ./register/

RUN npm install
RUN npm run build --workspace=@walkforpeace/register

FROM alpine:3.19
COPY --from=build /app/frontend/register/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Register frontend deployed'"]
