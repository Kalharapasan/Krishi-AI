import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiService {
  // Default to emulator localhost
  String baseUrl = 'http://127.0.0.1:8000/api';

  void updateBaseUrl(String newUrl) {
    baseUrl = newUrl;
    if (baseUrl.endsWith('/')) {
      baseUrl = baseUrl.substring(0, baseUrl.length - 1);
    }
  }

  Future<Map<String, dynamic>> uploadImageAndDiagnose(File imageFile) async {
    var uri = Uri.parse('$baseUrl/diagnose');
    var request = http.MultipartRequest('POST', uri);

    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        imageFile.path,
      ),
    );

    try {
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to diagnose: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to connect to backend: $e');
    }
  }

  Future<bool> submitFeedback(int recordId, String correctDisease) async {
    var uri = Uri.parse('$baseUrl/feedback');
    var response = await http.post(
      uri,
      body: {
        'record_id': recordId.toString(),
        'correct_disease': correctDisease,
      },
    );
    return response.statusCode == 200;
  }

  Future<Map<String, dynamic>> fetchSystemStatus() async {
    var uri = Uri.parse('$baseUrl/health');
    var response = await http.get(uri);

    if (response.statusCode == 200) {
      return json.decode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Failed to fetch system status: ${response.statusCode}');
  }
}
