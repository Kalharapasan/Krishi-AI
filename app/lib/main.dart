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
  int? _recordId;
  bool _isLoading = false;
  bool _feedbackSubmitted = false;
  final ApiService _apiService = ApiService();
  
  // Update this list with your actual classes
  final List<String> _diseases = ["Healthy", "Apple Scab", "Rice Leaf Smut", "Tomato Blight", "Unknown"];
  String? _selectedFeedback;

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: source);

    if (pickedFile != null) {
      setState(() {
        _image = File(pickedFile.path);
        _heatmapBytes = null;
        _result = '';
        _recordId = null;
        _feedbackSubmitted = false;
      });
    }
  }

  Future<void> _diagnose() async {
    if (_image == null) return;

    setState(() {
      _isLoading = true;
      _result = '';
      _heatmapBytes = null;
      _feedbackSubmitted = false;
    });

    try {
      final diagnosis = await _apiService.uploadImageAndDiagnose(_image!);
      setState(() {
        _result = "Disease: ${diagnosis['disease']}\nConfidence: ${diagnosis['confidence']}%";
        _recordId = diagnosis['id'];
        _selectedFeedback = diagnosis['disease'];
        
        // Decode base64 heatmap if present
        if (diagnosis['heatmap'] != null) {
          _heatmapBytes = base64Decode(diagnosis['heatmap']);
        }
      });
    } catch (e) {
      setState(() {
        _result = "Error: $e";
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _submitFeedback() async {
    if (_recordId == null || _selectedFeedback == null) return;
    
    setState(() => _isLoading = true);
    try {
      await _apiService.submitFeedback(_recordId!, _selectedFeedback!);
      setState(() {
        _feedbackSubmitted = true;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Feedback saved! Thanks for helping us learn.')),
        );
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to submit feedback: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showSettingsDialog() {
    TextEditingController urlController = TextEditingController(text: _apiService.baseUrl);
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Backend API Settings'),
          content: TextField(
            controller: urlController,
            decoration: const InputDecoration(
              labelText: 'Ngrok / Local API URL',
              hintText: 'http://10.0.2.2:8000/api',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                _apiService.updateBaseUrl(urlController.text);
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('API URL updated to: ${_apiService.baseUrl}')),
                );
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Krishi AI - XAI Edition'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: _showSettingsDialog,
            tooltip: 'Settings',
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (_image != null)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Expanded(
                        child: Column(
                          children: [
                            const Text('Original Image', style: TextStyle(fontWeight: FontWeight.bold)),
                            const SizedBox(height: 5),
                            Image.file(_image!, height: 180, fit: BoxFit.cover),
                          ],
                        ),
                      ),
                      if (_heatmapBytes != null) ...[
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            children: [
                              const Text('AI Heatmap (XAI)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue)),
                              const SizedBox(height: 5),
                              Image.memory(_heatmapBytes!, height: 180, fit: BoxFit.cover),
                            ],
                          ),
                        ),
                      ]
                    ],
                  )
                else
                  const Text('Select an image of a plant leaf'),
                  
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => _pickImage(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt),
                      label: const Text('Camera'),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton.icon(
                      onPressed: () => _pickImage(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library),
                      label: const Text('Gallery'),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: _image != null && !_isLoading ? _diagnose : null,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 15),
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                  child: _isLoading && _recordId == null
                      ? const CircularProgressIndicator(color: Colors.white) 
                      : const Text('Diagnose Image', style: TextStyle(fontSize: 18)),
                ),
                const SizedBox(height: 20),
                Text(
                  _result,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  textAlign: TextAlign.center,
                ),
                
                // Feedback UI Section
                if (_recordId != null && !_feedbackSubmitted) ...[
                  const Divider(height: 40, thickness: 2),
                  const Text("Was this correct?", style: TextStyle(fontSize: 16)),
                  const SizedBox(height: 10),
                  DropdownButton<String>(
                    value: _selectedFeedback,
                    items: _diseases.map((String value) {
                      return DropdownMenuItem<String>(
                        value: value,
                        child: Text(value),
                      );
                    }).toList(),
                    onChanged: (newValue) {
                      setState(() {
                        _selectedFeedback = newValue;
                      });
                    },
                  ),
                  const SizedBox(height: 10),
                  ElevatedButton(
                    onPressed: _isLoading ? null : _submitFeedback,
                    child: _isLoading 
                        ? const CircularProgressIndicator()
                        : const Text('Submit Feedback'),
                  )
                ]
              ],
            ),
          ),
        ),
      ),
    );
  }
}
