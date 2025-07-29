<template>
  <div class="container">
    <h1>Struk Scanner dengan Nuxt.js</h1>
    <div class="upload-area" :class="{ 'drag-over-active': isDragging }" @dragover.prevent="onDragOver"
      @dragleave="onDragLeave" @drop.prevent="onDrop">
      <input type="file" id="fileInput" ref="fileInput" accept="image/*" multiple @change="onFileChange"
        style="display: none;">
      <label for="fileInput" class="upload-button">Pilih Gambar Struk</label>
      <p>Atau seret & lepas gambar di sini</p>
      <div v-if="selectedFiles.length > 0" class="image-preview-container">
        <img v-for="(file, index) in selectedFiles" :key="index" :src="file.preview" class="image-preview">
      </div>
    </div>
    <button @click="processStruks" :disabled="!selectedFiles.length || loading">
      {{ loading ? 'Memproses...' : 'Proses Struk' }}
    </button>

    <div v-if="loading" class="loading-indicator">
      <div class="spinner"></div>
      <p>Memproses...</p>
    </div>

    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    <div v-if="results.length > 0" class="results-container">
      
      <div class="result-card">
        <template v-if="results[currentStrukIndex].error">
          <h3>Hasil Struk {{ currentStrukIndex + 1 }} (Error)</h3>
          <p class="error-message">Error: {{ results[currentStrukIndex].error }}</p>
          <p v-if="results[currentStrukIndex].file_name">File: {{ results[currentStrukIndex].file_name }}</p>
        </template>
        <template v-else>
          <h3>Hasil Struk {{ currentStrukIndex + 1 }}</h3>
          <p><strong>Invoice Number:</strong> {{ results[currentStrukIndex].invoice_number || 'N/A' }}</p>
          <p><strong>Tanggal:</strong> {{ results[currentStrukIndex].tanggal || 'N/A' }}</p>
          <h4>Merchant</h4>
          <p><strong>Nama Toko:</strong> {{ results[currentStrukIndex].merchant?.name || 'N/A' }}</p>
          <p><strong>Alamat:</strong> {{ results[currentStrukIndex].merchant?.address || 'N/A' }}</p>
          <p><strong>Telepon:</strong> {{ results[currentStrukIndex].merchant?.phone || 'N/A' }}</p>
          <p><strong>Email:</strong> {{ results[currentStrukIndex].merchant?.email || 'N/A' }}</p>
          <h4>Daftar Barang</h4>
          <ul>
            <li v-for="(item, itemIndex) in results[currentStrukIndex].items" :key="itemIndex">
              <span><strong>Nama OCR:</strong> {{ item.ocr_result?.name || 'N/A' }}</span>
              <span><strong>Qty:</strong> {{ item.ocr_result?.quantity || 'N/A' }}</span>
              <span><strong>Harga Satuan:</strong> {{ formatCurrency(item.ocr_result?.price) || 'N/A' }}</span>
              <span><strong>Subtotal:</strong> {{ formatCurrency(item.ocr_result?.total) || 'N/A' }}</span>
              
              <!-- Tambahan Akurasi -->
              <span><strong>Final Accuracy:</strong> {{ item.ocr_result?.Final_accuracy !== null &&
                item.ocr_result?.Final_accuracy !== undefined ? (item.ocr_result.Final_accuracy * 100).toFixed(2) + '%'
                : 'N/A' }}</span>
              <span><strong>Text Accuracy:</strong> {{ item.ocr_result?.text_accuracy !== null &&
                item.ocr_result?.text_accuracy !== undefined ? (item.ocr_result.text_accuracy * 100).toFixed(2) + '%' :
                'N/A' }}</span>
              <span><strong>Price Accuracy:</strong> {{ item.ocr_result?.price_accuracy !== null &&
                item.ocr_result?.price_accuracy !== undefined ? (item.ocr_result.price_accuracy * 100).toFixed(2) + '%'
                : 'N/A' }}</span>


<!-- Cocok atau tidak -->
<template v-if="item.id !== null && item.id !== undefined">
  <span><strong>Matched ID:</strong> {{ item.id }}</span>
  <span><strong>Matched Name:</strong> {{ item.name }}</span>
  <span><strong>Harga di Data Pusat:</strong> {{ formatCurrency(item.harga_di_datapusat) || 'N/A'
                }}</span>
              </template>
              <template v-else>
                <span style="color: red; font-weight: bold;">Tidak Cocok</span>
              </template>
              <!-- Keywords -->
              <span>
                <strong>Keywords Digunakan:</strong>
                {{ item.ocr_result?.keywords && item.ocr_result.keywords.length > 0 ? item.ocr_result.keywords.join(',') : '-' }}
              </span>
            </li>
          </ul>
          <p><strong>Grand Total:</strong> {{ formatCurrency(results[currentStrukIndex].grand_total) || 'N/A' }}</p>
        </template>
      </div>
      <div class="navigation-buttons">
        <button @click="showPrevStruk" :disabled="currentStrukIndex === 0">Sebelumnya</button>
        <span>Struk {{ currentStrukIndex + 1 }} dari {{ results.length }}</span>
        <button @click="showNextStruk" :disabled="currentStrukIndex === results.length - 1">Berikutnya</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedFiles = ref([]);
const results = ref([]);
const loading = ref(false);
const errorMessage = ref('');
const isDragging = ref(false);
const currentStrukIndex = ref(0);

const onFileChange = (event) => {
  const files = Array.from(event.target.files);
  updateSelectedFiles(files);
};

const onDragOver = (event) => {
  event.preventDefault();
  isDragging.value = true;
};

const onDragLeave = () => {
  isDragging.value = false;
};

const onDrop = (event) => {
  event.preventDefault();
  isDragging.value = false;
  const files = Array.from(event.dataTransfer.files).filter(file => file.type.startsWith('image/'));
  updateSelectedFiles(files);
};

const updateSelectedFiles = (files) => {
  selectedFiles.value = files.map(file => ({
    file: file,
    preview: URL.createObjectURL(file)
  }));
  results.value = [];
  errorMessage.value = '';
  currentStrukIndex.value = 0; // Reset index when new files are selected
};

const processStruks = async () => {
  if (selectedFiles.value.length === 0) {
    errorMessage.value = 'Silakan pilih setidaknya satu file gambar struk.';
    return;
  }

  loading.value = true;
  results.value = [];
  errorMessage.value = '';

  const formData = new FormData();
  selectedFiles.value.forEach(item => {
    formData.append('files', item.file);
  });

  try {
    const response = await fetch('http://127.0.0.1:8000/struk-batch', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { error: await response.text() };
      }
      // Check if errorData has 'detail' from FastAPI's HTTPException
      const detailMessage = errorData.detail ? (Array.isArray(errorData.detail) ? errorData.detail.map(d => d.msg).join(', ') : errorData.detail) : '';
      throw new Error(detailMessage || errorData.error || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    results.value = data;
    currentStrukIndex.value = 0;

  } catch (error) {
    console.error('Error:', error);
    errorMessage.value = `Terjadi kesalahan saat memproses: ${error.message}. Pastikan FastAPI Anda berjalan di http://127.0.0.1:8000 dan CORS sudah dikonfigurasi.`;
  } finally {
    loading.value = false;
  }
};

const showPrevStruk = () => {
  if (currentStrukIndex.value > 0) {
    currentStrukIndex.value--;
  }
};

const showNextStruk = () => {
  if (currentStrukIndex.value < results.value.length - 1) {
    currentStrukIndex.value++;
  }
};

const formatCurrency = (amount) => {
  // Handle null, undefined, or non-numeric values
  if (typeof amount !== 'number' || isNaN(amount) || amount === null || amount === undefined) {
    return 'N/A';
  }
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(amount);
};
</script>

<style>
/* CSS di sini akan secara otomatis diterapkan ke komponen ini. */
/* Anda juga bisa menempatkan CSS global di `assets/css/main.css` atau serupa */
h1 {
  color: #333;
  margin-bottom: 25px;
  font-size: 2.2em;
}

.upload-area {
  border: 2px dashed #a7d9b9;
  border-radius: 8px;
  padding: 40px 20px;
  margin-bottom: 25px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #e6f9ed;
}

.upload-area:hover,
.upload-area.drag-over-active {
  background-color: #d9f2e4;
}

.upload-button {
  background-color: #4CAF50;
  color: white;
  padding: 12px 25px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: bold;
  transition: background-color 0.3s ease;
  margin-bottom: 15px;
}

.upload-button:hover {
  background-color: #45a049;
}

.upload-area p {
  color: #666;
  font-size: 0.9em;
  margin-top: 10px;
}

button {
  /* Reusing styles for the process button */
  background-color: #007bff;
  color: white;
  padding: 12px 30px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: bold;
  transition: background-color 0.3s ease, opacity 0.3s ease;
  margin-top: 10px;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  opacity: 0.7;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

.image-preview-container {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-top: 20px;
  justify-content: center;
}

.image-preview {
  width: 150px;
  height: 150px;
  object-fit: contain;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 5px;
  background-color: #f9f9f9;
}

/* Loading Spinner */
.loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 30px;
  color: #555;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

/* Results Display */
.results-container {
  margin-top: 40px;
  /* Reduced margin-top for results container */
  text-align: left;
  border-top: 1px solid #eee;
  padding-top: 30px;
}

.result-card {
  background-color: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 25px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.result-card h3 {
  color: #2c3e50;
  margin-top: 0;
  margin-bottom: 15px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.result-card p {
  margin-bottom: 8px;
  color: #555;
  line-height: 1.5;
}

.result-card p strong {
  color: #333;
}

.result-card ul {
  list-style: none;
  padding: 0;
  margin-top: 15px;
  border-top: 1px dashed #eee;
  padding-top: 15px;
}

.result-card ul li {
  background-color: #ecf0f1;
  border-left: 4px solid #3498db;
  padding: 10px 15px;
  margin-bottom: 8px;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.result-card ul li span {
  flex: 1;
  min-width: 150px;
}

.result-card ul li span strong {
  color: #2980b9;
}

.error-message {
  background-color: #ffebeb;
  color: #cc0000;
  border: 1px solid #cc0000;
  border-radius: 8px;
  padding: 15px;
  margin-top: 20px;
  font-weight: bold;
}

/* Navigasi Tombol */
.navigation-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.navigation-buttons button {
  background-color: #28a745;
  /* Warna hijau sedikit berbeda */
  color: white;
  padding: 8px 15px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.9em;
  margin: 0 5px;
  /* Sedikit jarak antar tombol dan teks */
}

.navigation-buttons button:hover:not(:disabled) {
  background-color: #218838;
}

.navigation-buttons button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
  opacity: 0.7;
}

.navigation-buttons span {
  font-weight: bold;
  color: #333;
  font-size: 1.1em;
}
</style>