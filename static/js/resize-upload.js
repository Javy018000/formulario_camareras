/*
 * Reduce una foto en el propio celular ANTES de subirla.
 *
 * Así el servidor casi no gasta CPU (clave en hosting gratis con 100 seg/día)
 * y la subida es ~20x más liviana en datos móviles. Si el navegador es viejo
 * o algo falla, devuelve el archivo original y el servidor lo comprime igual.
 *
 * Uso en el submit del formulario (dentro de una función async):
 *   const formData = new FormData(form);
 *   await prepararFotoParaSubir(form.querySelector('input[type=file]'), formData, 'foto');
 *   fetch(url, { method: 'POST', body: formData });
 */
async function reducirImagen(file, maxLado = 1280, calidad = 0.75) {
    if (!file || !file.type || !file.type.startsWith('image/')) return file;

    // createImageBitmap respeta la orientación EXIF y es más rápido que <img>
    let bitmap;
    try {
        bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch (e) {
        return file;  // navegador sin soporte: que lo maneje el servidor
    }

    let { width, height } = bitmap;
    if (Math.max(width, height) > maxLado) {
        const escala = maxLado / Math.max(width, height);
        width = Math.round(width * escala);
        height = Math.round(height * escala);
    }

    try {
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        canvas.getContext('2d').drawImage(bitmap, 0, 0, width, height);
        if (bitmap.close) bitmap.close();

        const blob = await new Promise((resolve) =>
            canvas.toBlob(resolve, 'image/jpeg', calidad));
        // Solo usar la versión reducida si de verdad pesa menos
        if (blob && blob.size > 0 && blob.size < file.size) return blob;
    } catch (e) {
        /* cae al return de abajo */
    }
    return file;
}

/*
 * Toma el input de archivo, reduce la foto y la deja lista en el FormData
 * bajo el nombre de campo indicado. Si no hay foto seleccionada, no hace nada.
 */
async function prepararFotoParaSubir(inputFile, formData, campo = 'foto') {
    if (!inputFile || !inputFile.files || !inputFile.files[0]) return;
    const original = inputFile.files[0];
    const reducida = await reducirImagen(original);
    formData.set(campo, reducida, 'foto.jpg');
}
