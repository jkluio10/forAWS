const express = require('express');
const path = require('path');
const multer = require('multer');
const AWS = require('aws-sdk');

const app = express();

// 使用記憶體來暫存上傳檔案
const upload = multer({ storage: multer.memoryStorage() });

// AWS S3 直接使用 EC2 角色，不需要自己設定金鑰
const s3 = new AWS.S3(); // 這行就可以了，會自動抓 EC2 上的 IAM Role 權限

// 上傳到 S3 的函式
async function uploadToS3(fileBuffer, fileName, mimeType) {
    const params = {
        Bucket: 'ai-sales-voice-bucket', // 你的 S3 bucket 名稱
        Key: `uploads/${fileName}`,       // S3 上的檔案名稱
        Body: fileBuffer,                 // 檔案內容
        ContentType: mimeType             // 檔案類型 (ex: audio/wav)
    };
    return s3.upload(params).promise();    // 回傳 Promise
}

// 提供靜態檔案 (你的 index.html、錄音用的前端)
app.use(express.static(path.join(__dirname, 'public')));

// 接收錄音檔上傳
app.post('/upload', upload.single('audio'), async (req, res) => {
    try {
        const file = req.file;

        // 自動加上時間戳，避免檔名重複
        const timestamp = Date.now();
        const uniqueFileName = `${timestamp}-${file.originalname}`;

        const result = await uploadToS3(file.buffer, uniqueFileName, file.mimetype);
        console.log('上傳成功:', result.Location);
        res.send({ message: '上傳成功', url: result.Location });
    } catch (error) {
        console.error('上傳失敗:', error);
        res.status(500).send({ message: '上傳失敗', error });
    }
});

// 新增路由來取得最新音檔
app.get('/audio/latest', async (req, res) => {
    try {
        // 列出 'requestaudio' 資料夾中的所有檔案
        const params = {
            Bucket: 'ai-sales-voice-bucket',
            Prefix: 'requestaudio/',  // 指定資料夾路徑
        };

        const data = await s3.listObjectsV2(params).promise();

        if (data.Contents.length === 0) {
            return res.status(404).send({ message: '沒有找到音檔' });
        }

        // 根據修改時間排序檔案，取最新的檔案
        const latestFile = data.Contents.sort((a, b) => b.LastModified - a.LastModified)[0];

        console.log('最新音檔:', latestFile.Key);

        // 取得最新音檔的 URL
        const getObjectParams = {
            Bucket: 'ai-sales-voice-bucket',
            Key: latestFile.Key,
        };

        const audioData = await s3.getObject(getObjectParams).promise();

        // 回傳音檔的內容
        res.setHeader('Content-Type', audioData.ContentType);
        res.setHeader('Content-Disposition', 'inline; filename="' + latestFile.Key + '"');
        res.send(audioData.Body);
    } catch (error) {
        console.error('取得音檔失敗:', error);
        res.status(500).send({ message: '取得音檔失敗', error });
    }
});

// 啟動伺服器
const PORT = process.env.PORT || 80;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`伺服器運行中，請使用以下地址訪問：`);
    console.log(`公開 IP: http://35.93.210.219`);
    console.log(`公開 DNS: ec2-35-93-210-219.us-west-2.compute.amazonaws.com`);
});
