import { NextRequest, NextResponse } from "next/server";
import { executarMockAsk } from "@/lib/mock/dipamMockEngine";
import { AskParams } from "@/lib/dipamApi";

/**
 * Endpoint mock para /ask
 * 
 * Este endpoint é usado quando NEXT_PUBLIC_DIPAM_ENV=mock.
 * Retorna dados mockados baseados em arquivos JSON estáticos,
 * sem chamar o backend real no Cloud Run.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // Valida payload
    if (!body || typeof body.pergunta !== "string") {
      return NextResponse.json(
        { error: "Body must include 'pergunta' string" },
        { status: 400 }
      );
    }
    
    const payload: AskParams = {
      pergunta: body.pergunta,
      usuarioId: body.usuario_id || body.usuarioId,
      papel: body.papel,
    };
    
    // Executa motor mock
    const resposta = await executarMockAsk(payload);
    
    return NextResponse.json(resposta, { status: 200 });
  } catch (error) {
    console.error("[mock/ask] Erro:", error);
    
    const errorMessage = error instanceof Error 
      ? error.message 
      : "Erro ao processar requisição mock";
    
    return NextResponse.json(
      { error: errorMessage },
      { status: 500 }
    );
  }
}

