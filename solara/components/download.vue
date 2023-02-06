<template>
    <a @click="request_download = true">
        <jupyter-widget v-for="child in children" :key="child" :widget="child"></jupyter-widget>
    </a>
</template>

<script>
module.exports = {
    watch: {
        bytes(value) {
            console.log("this.request_download", this.request_download, this.bytes, this)
            if (this.request_download) {
                const a = document.createElement('a');
                a.download = this.filename;
                const blob = new Blob([this.bytes], { type: this.mime_type });
                const blobUrl = window.URL.createObjectURL(blob);
                a.href = blobUrl;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(() => {
                    // Make sure we clean up
                    window.URL.revokeObjectURL(blobUrl);
                }, 1000);
                this.request_download = false;
            }
        }
    }
}
</script>
