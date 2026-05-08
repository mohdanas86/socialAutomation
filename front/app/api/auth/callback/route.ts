import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams
    const code = searchParams.get('code')
    const error = searchParams.get('error')

    if (error) {
        return NextResponse.redirect(
            new URL(`/?error=${error}`, request.url)
        )
    }

    if (!code) {
        return NextResponse.redirect(
            new URL('/?error=no_code', request.url)
        )
    }

    try {
        // Call backend to exchange code for token
        const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/auth/callback?code=${code}`,
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            }
        )

        if (response.ok) {
            const data = await response.json()
            // Backend redirects with token, we just pass it through
            return NextResponse.redirect(
                new URL(
                    `/dashboard?token=${data.access_token}`,
                    request.url
                )
            )
        } else {
            return NextResponse.redirect(
                new URL('/?error=exchange_failed', request.url)
            )
        }
    } catch (error) {
        return NextResponse.redirect(
            new URL('/?error=server_error', request.url)
        )
    }
}
