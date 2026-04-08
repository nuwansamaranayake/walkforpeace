FROM node:20-alpine AS build
WORKDIR /app/frontend

# Create workspace root that only knows about shared + admin
RUN echo '{"private":true,"workspaces":["shared","admin"]}' > package.json
COPY frontend/shared/ ./shared/
COPY frontend/admin/ ./admin/

RUN npm install
RUN npm run build --workspace=@walkforpeace/admin

FROM alpine:3.19
COPY --from=build /app/frontend/admin/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Admin frontend deployed'"]
