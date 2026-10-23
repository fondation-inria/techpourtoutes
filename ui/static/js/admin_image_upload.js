'use strict';
{
    // Same steps as the funnel's `image_upload` component, without Alpine: shrink the image,
    // have the app sign its upload, put it straight into the bucket, keep only its key.
    const MAX_SIDE = 1200;

    class Refused extends Error {}

    async function shrink(file) {
        const bitmap = await createImageBitmap(file);
        const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(bitmap.width * scale);
        canvas.height = Math.round(bitmap.height * scale);
        const context = canvas.getContext('2d');
        context.imageSmoothingQuality = 'high';
        context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        bitmap.close();
        const webp = await encode(canvas, 'image/webp');
        if (webp.type === 'image/webp') return webp;
        // Safari hands back a PNG instead. JPEG has no transparency: paint it white, not black.
        context.globalCompositeOperation = 'destination-over';
        context.fillStyle = '#fff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        return encode(canvas, 'image/jpeg');
    }

    function encode(canvas, type) {
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => (blob ? resolve(blob) : reject()), type, 0.82);
        });
    }

    async function send(input, image) {
        const signed = await fetch(input.dataset.uploadUrl, {
            method: 'POST',
            headers: {'X-CSRFToken': input.form.elements.csrfmiddlewaretoken.value},
            body: new URLSearchParams({content_type: image.type, content_length: image.size})
        });
        if (signed.status === 400) throw new Refused((await signed.json()).error);
        if (!signed.ok) throw new Error(`HTTP ${signed.status}`);
        const upload = await signed.json();
        const stored = await fetch(upload.url, {method: 'PUT', headers: upload.headers, body: image});
        if (!stored.ok) throw new Error(`HTTP ${stored.status}`);
        return upload.key;
    }

    function setUp(input) {
        const widget = input.parentElement;
        const file = widget.querySelector('[data-image-file]');
        const preview = widget.querySelector('[data-image-preview]');
        const remove = widget.querySelector('[data-image-remove]');
        const status = widget.querySelector('[data-image-status]');
        const show = (message) => {
            status.textContent = message;
            status.hidden = !message;
        };
        const display = (key, url) => {
            input.value = key;
            preview.src = url;
            preview.hidden = !url;
            remove.hidden = !key;
        };

        file.addEventListener('change', async () => {
            const picked = file.files[0];
            file.value = '';
            if (!picked) return;
            if (!input.dataset.accept.split(',').includes(picked.type)) {
                show('Ce format n\'est pas accepté : importez une image JPG, PNG ou WebP.');
                return;
            }
            if (picked.size > Number(input.dataset.sourceMaxSize)) {
                show('Ce visuel est trop lourd : essayez avec une autre image.');
                return;
            }
            show('Import en cours…');
            file.disabled = true;
            try {
                const image = await shrink(picked);
                display(await send(input, image), URL.createObjectURL(image));
                show('');
            } catch (error) {
                if (error instanceof Refused) {
                    show(error.message);
                } else {
                    show('L\'import du visuel a échoué, veuillez réessayer.');
                    window.Sentry?.captureException(error);
                }
            }
            file.disabled = false;
        });
        remove.addEventListener('click', () => display('', ''));
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-image-upload]').forEach(setUp);
    });
}
