# Appsmith Build Notes

## Recommended datasource setup

Create two datasources:

1. PostgreSQL datasource
   - Host: `postgres`
   - Port: `5432`
   - Database: from `.env`
   - Username: from `.env`
   - Password: from `.env`

2. REST API datasource
   - Base URL: `http://api:8080`

## Recommended page strategy

### Home page
Use the REST datasource and call:
- `GET /summary`
- `GET /tasks`
- `GET /content-items`
- `GET /documents`
- `GET /trades`

### Tasks page
Use REST endpoints for create/update actions.

Suggested queries:
- `getTasks`
- `createTask`
- `updateTask`

### Documents page
- `getDocuments`
- `createDocument`

### Content page
- `getContentItems`
- `createContentItem`

## Fastest MVP pattern

- table widget for list views
- modal form for create/edit
- tabs for filtered views
- only use JS objects when you actually need shared transformations

## Good rule

Keep Appsmith as the portal layer.
Keep logic in the API or database.
Do not bury your real business logic inside random widget scripts.
