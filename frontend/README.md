# FRC System — Frontend Integration Placeholder

The FRC frontend will be built and hosted separately (different account).

## Integration Steps
1. Set `NEXT_PUBLIC_FRC_API_URL=https://<frc-backend>/api/v1` in frontend env
2. Add frontend domain to `CORS_ORIGINS` in FRC backend Vercel config
3. Auth: `POST /api/v1/auth/login` → returns `access_token`
4. Include `Authorization: Bearer <token>` on all requests
5. API docs: `https://<frc-backend>/docs`
