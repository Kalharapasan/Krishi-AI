import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;


class ModelNotLoadedException implements Exception {
  final String message;
  ModelNotLoadedException([this.message = 'AI model is not loaded on the backend yet.']);
  @override
  String toString() => message;
}

class ApiService {
  String baseUrl = 'https://regain-agile-army.ngrok-free.dev';

  void updateBaseUrl(String newUrl) {
    baseUrl = newUrl.trim();
    if (baseUrl.endsWith('/')) {
      baseUrl = baseUrl.substring(0, baseUrl.length - 1);
    }
  }

  Future<Map<String, dynamic>> uploadImageAndDiagnose(File imageFile) async {
    final uri     = Uri.parse('$baseUrl/diagnose');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    try {
      final streamed  = await request.send().timeout(const Duration(seconds: 60));
      final response  = await http.Response.fromStream(streamed);

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 503) {
        // ✅ FIXED: backend returns 503 when model isn't loaded yet
        throw ModelNotLoadedException();
      } else {
        throw Exception('Diagnosis failed (HTTP ${response.statusCode}): ${response.body}');
      }
    } on ModelNotLoadedException {
      rethrow;
    } on SocketException {
      throw Exception(
        'Cannot connect to backend at $baseUrl.\n'
        'Check that the backend is running and the URL is correct (tap ⚙️).',
      );
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }

  Future<bool> submitFeedback(int recordId, String correctDisease) async {
    final uri      = Uri.parse('$baseUrl/feedback');
    final response = await http.post(
      uri,
      body: {
        'record_id':       recordId.toString(),
        'correct_disease': correctDisease,
      },
    ).timeout(const Duration(seconds: 30));

    if (response.statusCode == 200) return true;
    throw Exception('Feedback submission failed (HTTP ${response.statusCode})');
  }
}
