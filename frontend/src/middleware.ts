import { type NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  // This middleware could redirect routes, but Next.js routing still requires proper file structure
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next|assets).*)'],
};
