import cors from "cors";
import express from "express";
import multer from "multer";
import { config } from "./config.js";
import { extractFeaturesFromUpload } from "./extract.js";
import { interpretPulse, normalizeFeatures } from "./pulse.js";
import { createAnalyzeSongRouter } from "./routes/analyzeSong.js";

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 100 * 1024 * 1024 },
});
const PORT = config.analyzePort;

app.use(cors());
app.use(express.json({ limit: "2mb" }));
app.use("/storage", express.static(config.storageRoot));

app.get("/health", (_req, res) => {
  res.json({ ok: true, service: "howard-vox-analyze", port: PORT });
});

app.use("/analyze-song", createAnalyzeSongRouter(upload));

app.post("/analyze", upload.single("file"), (req, res) => {
  try {
    const title = req.body?.title || req.file?.originalname || "Untitled vocal take";
    const notes = req.body?.notes || "";
    const clientFeatures = normalizeFeatures(req.body?.features ? JSON.parse(req.body.features) : {});
    const finish = (features, source, warnings = []) => {
      const interpretation = interpretPulse(features);

      res.json({
        ...features,
        title,
        notes,
        source,
        warnings,
        interpretation,
      });
    };

    if (!req.file?.buffer) {
      finish(clientFeatures, "api-client-features", ["No uploaded file was present, so server analysis used provided feature data."]);
      return;
    }

    extractFeaturesFromUpload(req.file.buffer)
      .then((serverFeatures) => {
        finish(serverFeatures, "api-server-extracted");
      })
      .catch((error) => {
        finish(
          clientFeatures,
          "api-client-fallback",
          [`Server-side decoding failed, so analysis fell back to provided feature data. ${error instanceof Error ? error.message : "Unknown decode failure."}`]
        );
      });
  } catch (error) {
    res.status(400).json({
      error: "ANALYZE_REQUEST_FAILED",
      message: error instanceof Error ? error.message : "Unknown analyze failure",
    });
  }
});

app.listen(PORT, () => {
  console.log(`HOWARD VOX analyze backend listening on http://127.0.0.1:${PORT}`);
});
