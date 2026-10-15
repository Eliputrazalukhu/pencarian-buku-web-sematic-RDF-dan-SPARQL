import os
import html
import streamlit as st
from rdflib import Graph
from SPARQLWrapper import SPARQLWrapper, JSON

# =========================================================
# 1. KONFIGURASI
# =========================================================
st.set_page_config(
    page_title="Portal Katalog Semantik",
    page_icon="📚",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TTL_PATH = os.path.join(BASE_DIR, "data_buku.ttl")

st.markdown("""
<style>
.main-title {
    font-size: 2.1rem;
    color: #1E3A8A;
    font-weight: 750;
    margin-bottom: .2rem;
}
.sub-title {
    font-size: 1rem;
    color: #64748B;
    margin-bottom: 1.5rem;
}
.book-card {
    background: #F8FAFC;
    border-left: 5px solid #2563EB;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: .8rem;
    overflow-wrap: anywhere;
}
.badge-uri {
    background: #DBEAFE;
    color: #1D4ED8;
    padding: 3px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: .8rem;
    overflow-wrap: anywhere;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-title">📚 Portal Katalog Semantik & Graf Pengetahuan</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="sub-title">Pencarian buku menggunakan RDF dan SPARQL, '
    'dengan opsi pengayaan Linked Data melalui DBpedia.</div>',
    unsafe_allow_html=True
)

# =========================================================
# 2. MEMUAT DATASET RDF LOKAL
# =========================================================
@st.cache_resource
def load_rdf_graph(path, modified_time):
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph

if not os.path.isfile(TTL_PATH):
    st.error(f"Dataset tidak ditemukan: {TTL_PATH}")
    st.info("Letakkan data_buku.ttl di folder yang sama dengan app.py.")
    st.stop()

try:
    g = load_rdf_graph(TTL_PATH, os.path.getmtime(TTL_PATH))
except Exception as e:
    st.error(f"Gagal membaca data_buku.ttl: {e}")
    st.stop()

# =========================================================
# 3. SIDEBAR
# =========================================================
with st.sidebar:
    st.header("📊 Knowledge Graph")
    st.metric("Total Triple RDF", len(g))
    st.divider()
    st.markdown("### Teknologi")
    st.markdown(
        "- Python dan Streamlit\n"
        "- RDF/Turtle\n"
        "- RDFLib dan SPARQL\n"
        "- DBpedia Linked Data"
    )
    st.caption("Dataset: data_buku.ttl")

# =========================================================
# 4. KUERI SPARQL LOKAL
# =========================================================
SPARQL_BOOKS = """
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT DISTINCT ?book ?title ?year ?publisher ?authorURI
WHERE {
    ?book a dbo:Book ;
          dc:title ?title .
    OPTIONAL { ?book dc:date ?year . }
    OPTIONAL { ?book dc:publisher ?publisher . }
    OPTIONAL { ?book dbo:author ?authorURI . }
}
ORDER BY ?title
"""

try:
    query_results = list(g.query(SPARQL_BOOKS))
except Exception as e:
    st.error(f"Kueri SPARQL gagal: {e}")
    st.info("Coba perbarui RDFLib: python -m pip install --upgrade rdflib")
    st.stop()

books = []
for row in query_results:
    books.append({
        "book": str(row.book),
        "title": str(row.title),
        "year": str(row.year) if row.year is not None else "Tidak diketahui",
        "publisher": str(row.publisher) if row.publisher is not None else "Tidak diketahui",
        "author": str(row.authorURI) if row.authorURI is not None else ""
    })

# =========================================================
# 5. PENCARIAN DAN FILTER
# =========================================================
col_search, col_filter = st.columns([4, 1])

with col_search:
    keyword = st.text_input(
        "🔍 Cari judul buku",
        placeholder="Contoh: Semantic, Artificial Intelligence, Linked Data"
    ).strip()

with col_filter:
    show_all = st.checkbox("Tampilkan semua", value=True)

st.caption(f"Dataset berhasil dibaca: {len(g)} triple RDF.")

if keyword or show_all:
    if keyword:
        filtered_books = [
            book for book in books
            if keyword.casefold() in book["title"].casefold()
        ]
    else:
        filtered_books = books

    if filtered_books:
        st.success(f"Ditemukan {len(filtered_books)} buku.")
        for book in filtered_books:
            title = html.escape(book["title"])
            year = html.escape(book["year"])
            publisher = html.escape(book["publisher"])
            book_uri = html.escape(book["book"])
            author_uri = html.escape(book["author"])

            with st.container():
                st.markdown(
                    f"""
                    <div class="book-card">
                      <h3 style="margin-top:0;color:#1E3A8A;">📖 {title}</h3>
                      <p><b>Tahun terbit:</b> {year}</p>
                      <p><b>Penerbit:</b> {publisher}</p>
                      <p><b>Book URI:</b><br><span class="badge-uri">{book_uri}</span></p>
                      <p><b>Author URI:</b><br><span class="badge-uri">{author_uri or "Belum tersedia"}</span></p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if author_uri:
                    with st.expander(f"👤 Profil penulis: {book['title']}"):
                        if st.button(
                            "Ambil profil dari DBpedia",
                            key="author_" + book["book"]
                        ):
                            query_author = f"""
                            PREFIX dbo: <http://dbpedia.org/ontology/>
                            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                            SELECT ?name ?abstract ?thumbnail WHERE {{
                              OPTIONAL {{
                                <{author_uri}> rdfs:label ?name .
                                FILTER(LANG(?name) = "en")
                              }}
                              OPTIONAL {{
                                <{author_uri}> dbo:abstract ?abstract .
                                FILTER(LANG(?abstract) = "en")
                              }}
                              OPTIONAL {{ <{author_uri}> dbo:thumbnail ?thumbnail . }}
                            }}
                            LIMIT 1
                            """
                            try:
                                client = SPARQLWrapper("https://dbpedia.org/sparql")
                                client.setQuery(query_author)
                                client.setReturnFormat(JSON)
                                client.setTimeout(8)
                                bindings = client.query().convert().get(
                                    "results", {}
                                ).get("bindings", [])

                                if not bindings:
                                    st.info("Profil tidak ditemukan di DBpedia.")
                                else:
                                    data = bindings[0]
                                    name = data.get("name", {}).get(
                                        "value", book["author"].rsplit("/", 1)[-1]
                                    )
                                    abstract = data.get("abstract", {}).get(
                                        "value", "Biografi belum tersedia."
                                    )
                                    thumbnail = data.get("thumbnail", {}).get("value")
                                    if thumbnail:
                                        st.image(thumbnail, width=140)
                                    st.subheader(name)
                                    st.write(abstract)
                                    st.link_button("Buka halaman penulis", author_uri)
                            except Exception as e:
                                st.warning(
                                    "DBpedia tidak dapat diakses. "
                                    "Pencarian buku lokal tetap berfungsi."
                                )
                                st.caption(str(e))
            st.divider()
    else:
        st.warning(
            "Buku tidak ditemukan untuk kata kunci tersebut. "
            "Coba Semantic, Artificial, Programming, atau Linked Data."
        )
else:
    st.info("Masukkan kata kunci atau centang 'Tampilkan semua'.")

# =========================================================
# 6. INSPEKTUR GRAF
# =========================================================
with st.expander("🛠️ Inspektur Graf Semantik"):
    tab1, tab2, tab3 = st.tabs(
        ["📄 Dataset Turtle", "🔍 Kueri SPARQL", "📈 Statistik"]
    )
    with tab1:
        try:
            with open(TTL_PATH, "r", encoding="utf-8") as file:
                ttl_text = file.read()
            st.code(ttl_text, language="turtle")
            st.download_button(
                "⬇️ Unduh dataset",
                data=ttl_text,
                file_name="data_buku.ttl",
                mime="text/turtle"
            )
        except OSError as e:
            st.error(f"Gagal membaca file: {e}")
    with tab2:
        st.code(SPARQL_BOOKS, language="sparql")
    with tab3:
        st.write(f"Total triple: **{len(g)}**")
        st.write(f"Subjek unik: **{len(set(g.subjects()))}**")
        st.write(f"Predikat unik: **{len(set(g.predicates()))}**")
        st.write(f"Objek unik: **{len(set(g.objects()))}**")

st.caption("Portal Katalog Semantik | RDF • SPARQL • Linked Open Data")
