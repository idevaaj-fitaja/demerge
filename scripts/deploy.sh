#!/bin/bash
# Deploy Demerge to Vercel + Fly.io + Supabase
set -e

echo "=== Demerge Deployment Script ==="
echo ""

# ── Prerequisites ──────────────────────────────────────────────
echo "Prerequisites:"
echo "  1. GitHub repository (create one first)"
echo "  2. Vercel account (vercel.com)"
echo "  3. Fly.io account (fly.io)"
echo "  4. Supabase project (supabase.com)"
echo ""

# ── 1. Supabase ────────────────────────────────────────────────
echo "=== [1/4] Supabase Setup ==="
echo ""
echo "1. Create project at https://supabase.com"
echo "2. Go to SQL Editor → paste supabase-schema.sql → Run"
echo "3. Go to Storage → Create bucket → name: 'documents'"
echo "4. Go to Project Settings → API → copy URL + anon key + service_role key"
echo ""

# ── 2. Backend (Fly.io) ───────────────────────────────────────
echo "=== [2/4] Backend (Fly.io) ==="
echo ""
echo "Install flyctl:"
echo "  curl -fsSL https://fly.io/install.sh | sh"
echo ""
echo "Login & launch:"
echo "  fly auth login"
echo "  fly launch --dockerfile Dockerfile"
echo ""
echo "Set environment variables:"
echo "  fly secrets set SUPABASE_URL=https://your-project.supabase.co"
echo "  fly secrets set SUPABASE_KEY=your-service-role-key"
echo "  fly secrets set SUPABASE_STORAGE_BUCKET=documents"
echo "  fly secrets set BACKEND_URL=https://demerge-api.fly.dev"
echo "  fly secrets set DEMERGE_PACKAGED=0"
echo ""
echo "Deploy:"
echo "  fly deploy"
echo ""

# ── 3. Frontend (Vercel) ──────────────────────────────────────
echo "=== [3/4] Frontend (Vercel) ==="
echo ""
echo "Install Vercel CLI:"
echo "  npm i -g vercel"
echo ""
echo "Deploy from frontend/ directory:"
echo "  cd frontend"
echo "  vercel --prod"
echo ""
echo "Set environment variable in Vercel dashboard:"
echo "  VITE_API_URL = https://demerge-api.fly.dev/api"
echo ""

# ── 4. Configure CORS ─────────────────────────────────────────
echo "=== [4/4] Final Steps ==="
echo ""
echo "1. Update CORS in .env or Fly.io secrets:"
echo "   CORS_ORIGINS = https://demerge.vercel.app"
echo ""
echo "2. Push code to GitHub:"
echo "   git add ."
echo "   git commit -m \"ready for deploy\""
echo "   git remote add origin <your-repo-url>"
echo "   git push -u origin main"
echo ""
echo "=== Done ==="
