// Credit for js example: https://github.com/mozilla/pdf.js/blob/master/examples/components/simpleviewer.mjs
<template :pdf_name_b64_map="pdf_name_b64_map" :current_file="current_file">
  <div id="pdfViewerRoot" :style="'height: ' + height">
    <div id="viewerContainer">
      <div id="viewer" class="pdfViewer"></div>
    </div>
  </div>
</template>

<script>
module.exports = {
  mounted() {
    console.log("Beginning PDF viewer initialization...");

    this.pdfjsUrl =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.3.136/pdf.min.mjs";
    this.viewerUrl =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.3.136/pdf_viewer.mjs";
    this.workerUrl =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.3.136/pdf.worker.min.mjs";
    this.sandboxUrl =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.3.136/pdf.sandbox.min.mjs";
    this.cssUrl =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.3.136/pdf_viewer.min.css";

    function loadScript(url, { isModule = true } = {}) {
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = url;
        script.async = true;
        if (isModule) {
          script.type = "module";
        }

        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }

    function loadCss(url) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = url;
      document.head.appendChild(link);
    }

    loadCss(this.cssUrl);

    loadScript(this.pdfjsUrl).then(() => {
      loadScript(this.viewerUrl).then(() => {
        console.log("Scripts loaded successfully!");
        this.initPdfjs();
      });
    });
  },
  methods: {
    initPdfjs() {
      if (!pdfjsLib.getDocument || !pdfjsViewer.PDFViewer) {
        // eslint-disable-next-line no-alert
        alert(
          "pdfjsLib not found! This means the scripts didn't load successfully."
        );
      }

      // The workerSrc property shall be specified.
      //
      pdfjsLib.GlobalWorkerOptions.workerSrc = this.workerUrl;

      // Some PDFs need external cmaps.
      //
      // const CMAP_URL = "../../node_modules/pdfjs-dist/cmaps/";
      const CMAP_PACKED = true;

      const ENABLE_XFA = true;
      // TODO: Enable search
      // const SEARCH_FOR = ""; // try "Mozilla";

      const SANDBOX_BUNDLE_SRC = this.sandboxUrl;

      const container = document.getElementById("viewerContainer");

      const eventBus = new pdfjsViewer.EventBus();

      // (Optionally) enable hyperlinks within PDF files.
      const pdfLinkService = new pdfjsViewer.PDFLinkService({
        eventBus,
      });

      // (Optionally) enable find controller.
      //   const pdfFindController = new pdfjsViewer.PDFFindController({
      //     eventBus,
      //     linkService: pdfLinkService,
      //   });

      // (Optionally) enable scripting support.
      //   const pdfScriptingManager = new pdfjsViewer.PDFScriptingManager({
      //     eventBus,
      //     sandboxBundleSrc: SANDBOX_BUNDLE_SRC,
      //   });

      const pdfViewer = new pdfjsViewer.PDFViewer({
        container,
        eventBus,
        linkService: pdfLinkService,
        // findController: pdfFindController,
        // scriptingManager: pdfScriptingManager,
      });
      pdfLinkService.setViewer(pdfViewer);
      //   pdfScriptingManager.setViewer(pdfViewer);

      eventBus.on("pagesinit", function () {
        // We can use pdfViewer now, e.g. let's change default scale.
        pdfViewer.currentScaleValue = "page-width";

        // if (SEARCH_FOR) {
        //   eventBus.dispatch("find", { type: "", query: SEARCH_FOR });
        // }
      });

      window.addEventListener("resize", () => {
        pdfViewer.currentScaleValue = "page-width";
      });
      this.pdfLinkService = pdfLinkService;
      this.pdfViewer = pdfViewer;
      this.eventBus = eventBus;
      this.oldFile = null;
    },

    loadPdf(name) {
      if (!name) {
        // Unset PDF data
        this.pdfViewer.setDocument(null);
        this.pdfLinkService.setDocument(null, null);
        this.oldFile = this.current_file;
        return;
      }
      if (this.current_file === this.oldFile) {
        console.log(`PDF ${name} already loaded.`);
        return;
      }
      this.oldFile = this.current_file;

      if (name in this.pdf_name_b64_map) {
        const b64Data = this.pdf_name_b64_map[name];
        const asciiData = atob(b64Data);
        const uint8Array = new Uint8Array(asciiData.length);
        for (let i = 0; i < asciiData.length; i++) {
          uint8Array[i] = asciiData.charCodeAt(i);
        }
        const loadingTask = pdfjsLib.getDocument({ data: uint8Array });
        loadingTask.promise.then((pdfDocument) => {
          this.pdfViewer.setDocument(pdfDocument);
          this.pdfLinkService.setDocument(pdfDocument, null);
        });
      } else {
        console.log("PDF not found in the map.");
      }
    },
  },
  watch: {
    current_file() {
      let value = this.current_file;
      if (value) {
        console.log(`Loading PDF ${value}...`);
      } else {
        console.log("Unsetting PDF data...");
      }
      this.loadPdf(value);
    },
  },
};
</script>

<style >
#viewerContainer {
  overflow: auto;
  position: absolute;
  height: 100%;
  width: 100%;
  display: flex;
  justify-content: center;
}

#pdfViewerRoot {
  position: relative;
}

.page {
  border: 1px solid black !important;
  margin: 5px !important;
}
</style>