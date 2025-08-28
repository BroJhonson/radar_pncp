// src/js/modules/favorites.js

const FAVORITOS_KEY = 'radarPncpFavoritos';

export function getFavoritos() {
    const favoritosJson = localStorage.getItem(FAVORITOS_KEY);
    try {
        return favoritosJson ? JSON.parse(favoritosJson) : [];
    } catch (e) {
        console.error("Erro ao parsear favoritos do localStorage:", e);
        localStorage.removeItem(FAVORITOS_KEY);
        return [];
    }
}

export function adicionarFavorito(pncpId) {
    if (!pncpId) return false;
    let favoritos = getFavoritos();
    if (!favoritos.includes(pncpId)) {
        favoritos.push(pncpId);
        localStorage.setItem(FAVORITOS_KEY, JSON.stringify(favoritos));
        console.log("Adicionado aos favoritos:", pncpId);
        return true;
    }
    return false;
}

export function removerFavorito(pncpId) {
    if (!pncpId) return false;
    let favoritos = getFavoritos();
    const index = favoritos.indexOf(pncpId);
    if (index > -1) {
        favoritos.splice(index, 1);
        localStorage.setItem(FAVORITOS_KEY, JSON.stringify(favoritos));
        console.log("Removido dos favoritos:", pncpId);
        return true;
    }
    return false;
}

export function isFavorito(pncpId) {
    if (!pncpId) return false;
    return getFavoritos().includes(pncpId);
}