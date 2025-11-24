/**
 * Importação estática dos dados mock Q1
 * Isso garante que os JSONs sejam incluídos no bundle do Next.js
 */

// Importa os JSONs diretamente usando caminho relativo - Next.js vai incluí-los no bundle
// Caminho relativo: lib/mock/mockData.ts -> mock/data/ = ../../mock/data/
import q1ClientesData from "../../mock/data/q1_clientes_sem_compra.json";
import q1EstatisticasData from "../../mock/data/q1_estatisticas.json";

// Exporta os dados normalizados
export const q1ClientesMock = Array.isArray(q1ClientesData) 
  ? q1ClientesData 
  : (q1ClientesData as any)?.default || q1ClientesData;

export const q1EstatisticasMock = (q1EstatisticasData as any)?.default || q1EstatisticasData;

