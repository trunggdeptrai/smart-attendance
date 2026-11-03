import streamlit as st

def apply_custom_css():
    st.markdown(
        """
        <style>
        /* Keep sidebar toggle button visible while hiding Streamlit default menu/footer */
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        .stDeployButton {display: none;}
        
        /* Make header container transparent and non-blocking, but keep sidebar collapse button active */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        
        /* Always show the toggle button to open sidebar when collapsed */
        [data-testid="stSidebarCollapsedControl"] {
            visibility: visible !important;
            display: flex !important;
            color: #1E3A8A !important;
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
            top: 1rem !important;
            left: 1rem !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stSidebarCollapsedControl"]:hover {
            background-color: #F1F5F9 !important;
            border-color: #CBD5E1 !important;
            transform: scale(1.05);
        }
        
        /* ==================================================== */
        /* GLOBAL TYPOGRAPHY STANDARDIZATION                    */
        /* ==================================================== */
        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
            color: #0F172A;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        /* Standardize H1: Main Page Titles */
        h1, [data-testid="stHeader"] h1, .stHeadingContainer h1 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            font-size: 2.0rem !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            letter-spacing: -0.025em !important;
            line-height: 1.25 !important;
            margin-bottom: 0.25rem !important;
        }

        /* Standardize H2 & H3: Section Titles */
        h2, h3, [data-testid="stHeader"] h2, [data-testid="stHeader"] h3,
        .stHeadingContainer h2, .stHeadingContainer h3 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            font-size: 1.25rem !important;
            font-weight: 600 !important;
            color: #1E3A8A !important;
            letter-spacing: -0.015em !important;
            line-height: 1.35 !important;
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }

        /* Standardize Subtitles & Secondary Descriptions */
        .stMarkdown p {
            font-size: 0.95rem;
            color: #334155;
            line-height: 1.5;
        }

        /* Captions and subtext */
        .stCaption, [data-testid="stCaptionContainer"] {
            font-size: 0.88rem !important;
            color: #64748B !important;
            line-height: 1.4 !important;
        }
        
        /* Add comfortable top padding */
        .block-container {
            padding-top: 3.5rem;
            padding-bottom: 2rem;
        }
        
        /* Modern buttons */
        .stButton>button {
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transform: translateY(-1px);
        }
        
        /* Metric cards styling: Uniform height, rounded-xl (14px), soft multi-layer shadow */
        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            min-height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border: 1px solid #E2E8F0;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        [data-testid="stMetric"]:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
            border-color: #CBD5E1;
            transform: translateY(-2px);
        }

        /* Metric label typography */
        [data-testid="stMetricLabel"] {
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            color: #64748B !important;
            letter-spacing: -0.01em;
            margin-bottom: 0.25rem;
        }

        /* Metric value typography */
        [data-testid="stMetricValue"] {
            font-size: 1.85rem !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            line-height: 1.2;
        }

        /* Metric delta badge styling */
        [data-testid="stMetricDelta"] {
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            margin-top: 0.25rem;
        }
        
        /* ==================================================== */
        /* CONTAINER, CARDS & SPACING STANDARDIZATION           */
        /* ==================================================== */
        /* Standardize st.container(border=True) wrappers */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px !important;
            border: 1px solid #E2E8F0 !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
            transition: box-shadow 0.2s ease, border-color 0.2s ease !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #CBD5E1 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        }

        /* Standardize internal padding for border containers */
        [data-testid="stVerticalBlockBorderWrapper"] > div:first-child {
            padding: 1.25rem 1.5rem !important;
        }

        /* Clean Enterprise Dividers (hr / st.divider) */
        hr, [data-testid="stDivider"] {
            border: none !important;
            border-top: 1px solid #E2E8F0 !important;
            margin: 1.25rem 0 !important;
        }

        /* Clean Enterprise Dataframe Styling */
        [data-testid="stDataFrame"] {
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04) !important;
        }

        /* ==================================================== */
        /* SIDEBAR ENHANCEMENTS & TYPOGRAPHY                    */
        /* ==================================================== */
        /* Sidebar container spacing & subtle border */
        [data-testid="stSidebar"] {
            border-right: 1px solid #E2E8F0;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* Brand title & caption in sidebar */
        [data-testid="stSidebar"] h1 {
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: #1E3A8A !important;
            margin-bottom: 0.15rem !important;
            letter-spacing: -0.02em;
        }

        [data-testid="stSidebar"] .stCaption {
            font-size: 0.8rem !important;
            color: #64748B !important;
            margin-bottom: 1.5rem !important;
        }

        /* Section headers in navigation (e.g., Quản lý, Nhận diện AI) */
        [data-testid="stSidebarNav"] span[data-testid="stSidebarNavSectionHeader"] {
            font-size: 0.75rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: #64748B !important;
            margin-top: 1rem !important;
            margin-bottom: 0.35rem !important;
            padding-left: 0.5rem !important;
        }

        /* Sidebar navigation links */
        [data-testid="stSidebarNav"] ul {
            padding: 0 !important;
        }

        [data-testid="stSidebarNav"] li {
            margin-bottom: 0.25rem !important;
        }

        [data-testid="stSidebarNav"] a {
            padding: 0.55rem 0.85rem !important;
            border-radius: 8px !important;
            font-size: 0.92rem !important;
            font-weight: 500 !important;
            color: #334155 !important;
            transition: all 0.15s ease-in-out !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.65rem !important;
        }

        /* Hover effect on menu item */
        [data-testid="stSidebarNav"] a:hover {
            background-color: #F1F5F9 !important;
            color: #1E3A8A !important;
            transform: translateX(2px);
        }

        /* Active / Selected menu item */
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: #EEF2FF !important;
            color: #1E3A8A !important;
            font-weight: 600 !important;
            border-left: 3.5px solid #1E3A8A !important;
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 3.25rem 1rem 1.5rem;
            }

            h1, [data-testid="stHeader"] h1 {
                font-size: 1.55rem !important;
            }

            [data-testid="stMetric"] {
                padding: 0.85rem;
                min-height: 92px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )
