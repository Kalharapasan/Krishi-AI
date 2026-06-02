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