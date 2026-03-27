from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_block = '''def _render_dataframe(df: pd.DataFrame, **kwargs):
    display_df = _clean_dataframe(df)
    _render_dataframe(display_df, **kwargs)
'''

new_block = '''def _render_dataframe(df: pd.DataFrame, **kwargs):
    display_df = _clean_dataframe(df)
    try:
        st.dataframe(display_df, **kwargs)
    except Exception:
        fallback_df = display_df.copy()
        fallback_df = fallback_df.loc[:, ~fallback_df.columns.duplicated()].copy()
        for col in fallback_df.columns:
            fallback_df[col] = fallback_df[col].map(
                lambda v: float(v) if isinstance(v, Decimal) else _pretty_text_value(v)
            )
        st.dataframe(fallback_df, **kwargs)
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")

    original = TARGET.read_text(encoding="utf-8")
    if old_block not in original:
        raise SystemExit("Could not find recursive _render_dataframe block to replace.")

    updated = original.replace(old_block, new_block, 1)
    backup = TARGET.with_name(TARGET.name + ".bak_runtime_fix_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(updated, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
