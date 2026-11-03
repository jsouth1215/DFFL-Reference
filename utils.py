import streamlit as st

def render_html_table(df, highlight_fn=None, left_align_cols=None):
    styler = df.style.hide(axis='index')
    styler = styler.set_properties(**{
        'text-align': 'center',
        'padding': '6px 8px',
        'border': '1px solid #e6e6e6',
        'white-space': 'nowrap'
    })
    if left_align_cols:
        valid_cols = [c for c in left_align_cols if c in df.columns]
        if valid_cols:
            styler = styler.set_properties(subset=valid_cols, **{'text-align': 'left'})
    if highlight_fn:
        styler = styler.apply(highlight_fn, axis=1)
        
    styled_html = styler.set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '6px 8px'), ('border', '1px solid #e6e6e6'), ('white-space', 'nowrap')]},
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
    ]).to_html()
    st.markdown(styled_html, unsafe_allow_html=True)

def format_ordinal(val):
    if not val or str(val).strip() == "":
        return ""
    try:
        n = int(float(val))
        suffix = 'th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    except:
        return str(val)
      
