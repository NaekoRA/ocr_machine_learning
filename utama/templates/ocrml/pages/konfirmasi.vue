<template>
  <div class="page-container">
    <h2>Konfirmasi Hasil OCR</h2>

    <div v-if="loading" class="loading-indicator">
      <div class="spinner"></div>
      <p>Memuat data struk...</p>
    </div>

    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
    <div v-if="unconfirmedReceipts.length === 0 && !loading">Tidak ada struk yang perlu dikonfirmasi.</div>

    <div v-if="unconfirmedReceipts.length > 0" class="receipt-card">
      <h3>Struk #{{ currentReceipt.receipt_id }}</h3>
      <p><strong>Invoice:</strong> {{ currentReceipt.receipt_data.invoice_number }}</p>
      <p><strong>Tanggal:</strong> {{ currentReceipt.receipt_data.tanggal }}</p>
      <p><strong>Toko:</strong> {{ currentReceipt.receipt_data.nama_toko }}</p>
      <p><strong>Alamat:</strong> {{ currentReceipt.receipt_data.alamat }}</p>
      <p><strong>Telepon:</strong> {{ currentReceipt.receipt_data.phone || 'N/A' }}</p>
      <p><strong>Email:</strong> {{ currentReceipt.receipt_data.email || 'N/A' }}</p>

      <h4>Barang</h4>
      <ul>
        <li v-for="(item, i) in currentReceipt.matched_data" :key="i" class="item-card">
          <p><strong>OCR Nama:</strong> {{ item.ocr_result.name }}</p>
          <p><strong>Qty:</strong> {{ item.ocr_result.quantity }} | <strong>Harga:</strong> {{
            formatCurrency(item.ocr_result.price) }} | <strong>Subtotal:</strong> {{
              formatCurrency(item.ocr_result.total) }}</p>
          <p><strong>Akurasi:</strong> {{ (item.ocr_result.Final_accuracy * 100).toFixed(2) }}%</p>
          <p v-if="item.id"><strong>Matched:</strong> {{ item.name }}</p>
          <p v-else class="no-match">Tidak ditemukan di database pusat</p>
          <p><strong>Keywords Digunakan:</strong>
            {{ item.ocr_result?.keywords?.length > 0 ? item.ocr_result.keywords.join(', ') : '-' }}
          </p>
        </li>
      </ul>

      <p><strong>Total Belanja:</strong> {{ formatCurrency(currentReceipt.receipt_data.total_belanja) }}</p>

      <div class="feedback-box">
        <label for="feedback">Feedback:</label>
        <input
          type="text"
          v-model="feedbacks[currentIndex]"
          placeholder="Tulis feedback jika perlu..."
        />
      </div>

      <div class="actions">
        <button class="btn benar" @click="confirmReceipt(currentReceipt.receipt_id, true)">Konfirmasi Benar</button>
        <button class="btn salah" @click="confirmReceipt(currentReceipt.receipt_id, false)">Konfirmasi Salah</button>
      </div>

      <div class="navigation-buttons" v-if="unconfirmedReceipts.length > 1">
        <button @click="showPrev" :disabled="currentIndex === 0">Sebelumnya</button>
        <span>Struk {{ currentIndex + 1 }} dari {{ unconfirmedReceipts.length }}</span>
        <button @click="showNext" :disabled="currentIndex === unconfirmedReceipts.length - 1">Berikutnya</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Swal from 'sweetalert2'

const unconfirmedReceipts = ref([])
const feedbacks = ref([])
const loading = ref(true)
const errorMessage = ref('')

const fetchUnconfirmed = async () => {
  try {
    const res = await fetch('http://localhost:8000/ocr/unconfirmed')
    if (!res.ok) throw new Error('Gagal memuat data')
    const data = await res.json()
    unconfirmedReceipts.value = data
    feedbacks.value = new Array(data.length).fill('')
    currentIndex.value = 0
  } catch (err) {
    errorMessage.value = 'Terjadi kesalahan: ' + err.message
  } finally {
    loading.value = false
  }
}


const confirmReceipt = async (receiptId, isCorrect) => {
  try {
    const res = await fetch(`http://localhost:8000/confirm-ocr/${receiptId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        is_correct: isCorrect,
        feedback: feedbacks.value[currentIndex.value] || ''
      })
    })
    if (!res.ok) throw new Error('Gagal mengkonfirmasi')

    await Swal.fire({
      icon: 'success',
      title: 'Berhasil!',
      text: 'Struk berhasil dikonfirmasi.',
      timer: 1800,
      showConfirmButton: false
    })

    await fetchUnconfirmed()
  } catch (err) {
    Swal.fire({
      icon: 'error',
      title: 'Gagal!',
      text: 'Gagal konfirmasi: ' + err.message,
    })
  }
}

const formatCurrency = (amount) => {
  if (typeof amount !== 'number' || isNaN(amount)) return 'N/A'
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR'
  }).format(amount)
}

onMounted(fetchUnconfirmed)
const currentIndex = ref(0);
const currentReceipt = computed(() => unconfirmedReceipts.value[currentIndex.value]);

const showPrev = () => {
  if (currentIndex.value > 0) currentIndex.value--;
};

const showNext = () => {
  if (currentIndex.value < unconfirmedReceipts.value.length - 1) currentIndex.value++;
};
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.receipt-card {
  background: #f9f9f9;
  border: 1px solid #ddd;
  padding: 20px;
  border-radius: 10px;
  margin-bottom: 30px;
}

.item-card {
  background: #eef5f7;
  border-left: 4px solid #3498db;
  padding: 10px 15px;
  margin-bottom: 15px;
  border-radius: 5px;
}

.actions {
  margin-top: 15px;
}

.btn {
  padding: 8px 20px;
  margin-right: 10px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
}

.benar {
  background-color: #4CAF50;
  color: white;
}

.salah {
  background-color: #F44336;
  color: white;
}

.no-match {
  color: red;
  font-weight: bold;
}

.loading-indicator {
  text-align: center;
  margin: 30px 0;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 4px solid #ccc;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  margin: auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.error-message {
  background: #ffe5e5;
  color: #cc0000;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 8px;
}

.feedback-box {
  margin-top: 15px;
}

.feedback-box input {
  width: 100%;
  padding: 8px;
  border-radius: 5px;
  border: 1px solid #ccc;
  margin-top: 5px;
}
</style>
