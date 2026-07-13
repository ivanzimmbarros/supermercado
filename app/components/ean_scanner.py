"""Widget reutilizável de scanner EAN (câmara / upload / manual)."""

from __future__ import annotations

import streamlit as st

from supermercado.scanning.ean import decode_ean_from_bytes, validate_ean


def render_ean_scanner(key_prefix: str = "ean") -> str | None:
    """
    Mostra UI de scanner e devolve EAN válido seleccionado, ou None.
    O valor é também guardado em st.session_state[f'{key_prefix}_value'].
    """
    state_key = f"{key_prefix}_value"
    st.markdown("##### Scanner EAN")
    mode = st.radio(
        "Origem do código",
        options=["Manual", "Câmara", "Upload"],
        horizontal=True,
        key=f"{key_prefix}_mode",
    )

    candidate: str | None = st.session_state.get(state_key)

    if mode == "Manual":
        typed = st.text_input(
            "EAN (8 ou 13 dígitos)",
            value=candidate or "",
            key=f"{key_prefix}_manual",
        )
        if typed:
            result = validate_ean(typed)
            if result.ok:
                st.session_state[state_key] = result.ean
                st.caption(f"Válido ({result.symbology})")
            else:
                st.warning(result.message)
                if result.ean:
                    st.session_state[state_key] = result.ean  # permite tentativa mesmo assim
    elif mode == "Câmara":
        photo = st.camera_input("Apontar ao código de barras", key=f"{key_prefix}_cam")
        if photo is not None:
            result = decode_ean_from_bytes(photo.getvalue())
            if result.ok:
                st.success(f"Lido: {result.ean}")
                st.session_state[state_key] = result.ean
            else:
                st.warning(result.message)
                if result.ean:
                    st.session_state[state_key] = result.ean
    else:
        upload = st.file_uploader(
            "Fotografia / imagem do código",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"{key_prefix}_upload",
        )
        if upload is not None:
            result = decode_ean_from_bytes(upload.getvalue())
            if result.ok:
                st.success(f"Lido: {result.ean}")
                st.session_state[state_key] = result.ean
            else:
                st.warning(result.message)
                if result.ean:
                    st.session_state[state_key] = result.ean

    final = st.session_state.get(state_key)
    if final:
        st.info(f"EAN em uso: `{final}`")
    return final
