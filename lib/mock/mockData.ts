/**
 * Carregamento dinâmico dos dados mock Q1
 * Usa require() dinâmico para evitar problemas de resolução de módulos no build
 */

let q1ClientesMock: any[] | null = null;
let q1EstatisticasMock: any | null = null;

// Função para carregar dados (lazy loading)
export function getQ1ClientesMock(): any[] {
  if (q1ClientesMock === null) {
    try {
      // Tenta diferentes caminhos possíveis
      const paths = [
        require("../../mock/data/q1_clientes_sem_compra.json"),
        require("../../../mock/data/q1_clientes_sem_compra.json"),
        require("@/mock/data/q1_clientes_sem_compra.json"),
      ];
      
      for (const data of paths) {
        if (data) {
          q1ClientesMock = Array.isArray(data) ? data : (data?.default || data);
          if (q1ClientesMock && q1ClientesMock.length > 0) {
            break;
          }
        }
      }
    } catch (e) {
      console.error("[mockData] Erro ao carregar q1_clientes_sem_compra.json:", e);
      q1ClientesMock = [];
    }
  }
  return q1ClientesMock || [];
}

export function getQ1EstatisticasMock(): any {
  if (q1EstatisticasMock === null) {
    try {
      const paths = [
        require("../../mock/data/q1_estatisticas.json"),
        require("../../../mock/data/q1_estatisticas.json"),
        require("@/mock/data/q1_estatisticas.json"),
      ];
      
      for (const data of paths) {
        if (data) {
          q1EstatisticasMock = data?.default || data;
          if (q1EstatisticasMock && q1EstatisticasMock.total_clientes) {
            break;
          }
        }
      }
    } catch (e) {
      console.error("[mockData] Erro ao carregar q1_estatisticas.json:", e);
      q1EstatisticasMock = {};
    }
  }
  return q1EstatisticasMock || {};
}

