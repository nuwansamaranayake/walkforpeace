FROM node:20-alpine AS build
WORKDIR /app/frontend

# Create workspace root that only knows about shared + verify
RUN echo '{"private":true,"workspaces":["shared","verify"]}' > package.json
COPY frontend/shared/ ./shared/
COPY frontend/verify/ ./verify/

RUN npm install
RUN npm run build --workspace=@walkforpeace/verify

FROM alpine:3.19
COPY --from=build /app/frontend/verify/dist /build-output
CMD ["sh", "-c", "cp -r /build-output/* /app/dist/ 2>/dev/null; echo 'Verify frontend deployed'"]
