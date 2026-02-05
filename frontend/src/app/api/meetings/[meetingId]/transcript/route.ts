import { NextRequest, NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ meetingId: string }> }
) {
  try {
    const { meetingId } = await params
    
    const response = await fetch(`${BACKEND_BASE}/meetings/${meetingId}/transcript`, {
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return new NextResponse('', { status: 200 })
    }
    
    const text = await response.text()
    return new NextResponse(text, { 
      status: 200,
      headers: { 'Content-Type': 'text/plain' }
    })
  } catch (error: any) {
    console.error('[API Proxy] Transcript Error:', error.message)
    return new NextResponse('', { status: 200 })
  }
}
