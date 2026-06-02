import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'api_service.dart';

void main() {
  runApp(const KrishiApp());
}

class KrishiApp extends StatelessWidget {
  const KrishiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Krishi AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  File? _image;
  Uint8List? _heatmapBytes;
  String _result = '';
  String _resultDisease = '';
  double _resultConfidence = 0;
  int? _recordId;
  bool _isLoading = false;
  bool _feedbackSubmitted = false;
  bool _modelNotLoaded = false;
  final ApiService _apiService = ApiService();

  // ✅ FIXED: All 38 real PlantVillage class names (must match backend config.py)
  final List<String> _diseases = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
  ];
  String? _selectedFeedback;

  // Format raw class name for display e.g. "Tomato___Early_blight" → "Tomato - Early Blight"
  String _formatDiseaseName(String raw) {
    final parts = raw.split('___');
    if (parts.length == 2) {
      final plant   = parts[0].replaceAll('_', ' ');
      final disease = parts[1].replaceAll('_', ' ');
      return '$plant — $disease';
    }
    return raw.replaceAll('_', ' ');
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker     = ImagePicker();
    final pickedFile = await picker.pickImage(source: source, imageQuality: 85);
    if (pickedFile != null) {
      setState(() {
        _image            = File(pickedFile.path);
        _heatmapBytes     = null;
        _result           = '';
        _resultDisease    = '';
        _resultConfidence = 0;
        _recordId         = null;
        _feedbackSubmitted = false;
        _modelNotLoaded   = false;
      });
    }
  }

  Future<void> _diagnose() async {
    if (_image == null) return;
    setState(() {
      _isLoading      = true;
      _result         = '';
      _heatmapBytes   = null;
      _feedbackSubmitted = false;
      _modelNotLoaded = false;
    });

    try {
      final diagnosis = await _apiService.uploadImageAndDiagnose(_image!);
      setState(() {
        _resultDisease    = diagnosis['disease'] as String;
        _resultConfidence = (diagnosis['confidence'] as num).toDouble();
        _result           = "Disease: ${_formatDiseaseName(_resultDisease)}\n"
                            "Confidence: ${_resultConfidence.toStringAsFixed(1)}%";
        _recordId         = diagnosis['id'] as int?;
        _selectedFeedback = _resultDisease;

        if (diagnosis['heatmap'] != null) {
          _heatmapBytes = base64Decode(diagnosis['heatmap'] as String);
        }
      });
    } on ModelNotLoadedException {
      // ✅ FIXED: friendly message when backend has no model yet
      setState(() {
        _modelNotLoaded = true;
        _result = '';
      });
    } catch (e) {
      setState(() {
        _result = "Error: $e";
      });
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submitFeedback() async {
    if (_recordId == null || _selectedFeedback == null) return;
    setState(() => _isLoading = true);
    try {
      await _apiService.submitFeedback(_recordId!, _selectedFeedback!);
      setState(() => _feedbackSubmitted = true);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Feedback saved! Thanks for helping Krishi AI learn.'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit feedback: $e')),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showSettingsDialog() {
    final urlController = TextEditingController(text: _apiService.baseUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Backend API Settings'),
        content: TextField(
          controller: urlController,
          decoration: const InputDecoration(
            labelText: 'Backend / Ngrok URL',
            hintText: 'https://regain-agile-army.ngrok-free.dev',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              _apiService.updateBaseUrl(urlController.text.trim());
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('API URL updated to: ${_apiService.baseUrl}')),
              );
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Color _confidenceColor(double confidence) {
    if (confidence >= 80) return Colors.green;
    if (confidence >= 50) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🌿 Krishi AI'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettingsDialog,
            tooltip: 'API Settings',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // ── Image Preview ──────────────────────────────────────────────
            if (_image != null) ...[
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Expanded(
                    child: Column(children: [
                      const Text('Original', style: TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(_image!, height: 180, fit: BoxFit.cover),
                      ),
                    ]),
                  ),
                  if (_heatmapBytes != null) ...[
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(children: [
                        const Text(
                          'AI Heatmap (XAI)',
                          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue),
                        ),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.memory(_heatmapBytes!, height: 180, fit: BoxFit.cover),
                        ),
                      ]),
                    ),
                  ],
                ],
              ),
            ] else ...[
              Container(
                height: 180,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.eco, size: 48, color: Colors.green),
                    SizedBox(height: 8),
                    Text('Take or select a photo of a plant leaf',
                        style: TextStyle(color: Colors.grey)),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 20),

            // ── Pick Image Buttons ─────────────────────────────────────────
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _pickImage(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Camera'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : () => _pickImage(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Gallery'),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // ── Diagnose Button ───────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: (_image != null && !_isLoading) ? _diagnose : null,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: _isLoading && _recordId == null
                    ? const SizedBox(
                        height: 22, width: 22,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                      )
                    : const Text('Diagnose Plant', style: TextStyle(fontSize: 17)),
              ),
            ),

            const SizedBox(height: 20),

            // ── Model Not Loaded Warning ──────────────────────────────────
            if (_modelNotLoaded)
              Card(
                color: Colors.orange.shade50,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 36),
                    const SizedBox(height: 8),
                    const Text(
                      'Model Not Ready',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'The AI model has not been trained yet.\n'
                      '1. Open the Colab notebook and train the model.\n'
                      '2. The model will upload to the backend automatically.\n'
                      '3. Come back and diagnose!',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.black87),
                    ),
                    const SizedBox(height: 10),
                    TextButton.icon(
                      onPressed: _showSettingsDialog,
                      icon: const Icon(Icons.settings),
                      label: const Text('Check API URL'),
                    ),
                  ]),
                ),
              ),

            // ── Result Card ───────────────────────────────────────────────
            if (_result.isNotEmpty && !_modelNotLoaded)
              Card(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                elevation: 3,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(children: [
                    Text(
                      _formatDiseaseName(_resultDisease),
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Confidence: ', style: TextStyle(fontSize: 15)),
                        Text(
                          '${_resultConfidence.toStringAsFixed(1)}%',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: _confidenceColor(_resultConfidence),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    LinearProgressIndicator(
                      value: _resultConfidence / 100,
                      color: _confidenceColor(_resultConfidence),
                      backgroundColor: Colors.grey.shade200,
                      minHeight: 8,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ]),
                ),
              ),

            // ── Feedback Section ──────────────────────────────────────────
            if (_recordId != null && !_feedbackSubmitted && !_modelNotLoaded) ...[
              const Divider(height: 36, thickness: 1.5),
              const Text(
                'Was this diagnosis correct?',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _selectedFeedback,
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: 'Select correct disease',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                items: _diseases.map((String value) {
                  return DropdownMenuItem<String>(
                    value: value,
                    child: Text(_formatDiseaseName(value), overflow: TextOverflow.ellipsis),
                  );
                }).toList(),
                onChanged: (newValue) => setState(() => _selectedFeedback = newValue),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isLoading ? null : _submitFeedback,
                  icon: const Icon(Icons.thumb_up_alt_outlined),
                  label: _isLoading
                      ? const SizedBox(
                          height: 18, width: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Submit Feedback'),
                ),
              ),
            ],

            if (_feedbackSubmitted)
              const Padding(
                padding: EdgeInsets.only(top: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle, color: Colors.green),
                    SizedBox(width: 6),
                    Text('Feedback submitted! Thank you.', style: TextStyle(color: Colors.green)),
                  ],
                ),
              ),

            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}
