#include <portaudio.h>
#include <vector>
#include <mutex>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

namespace py = pybind11;

struct Voice {
    int pad_id;
    size_t pos;
    float velocity;
    float reverb_send;
    float delay_send;
    bool active;
    int start_delay_frames; // New: frames to wait before playing
};

class CppAudioEngine {
public:
    CppAudioEngine(int sample_rate = 44100) : sample_rate_(sample_rate), stream_(nullptr) {
        // Initialize PortAudio
        Pa_Initialize();
        
        // Initialize Effects Buffers
        delay_len_ = sample_rate * 2; // 2 seconds
        delay_buffer_.resize(delay_len_ * 2, 0.0f); // Stereo
        delay_write_pos_ = 0;
        delay_time_samples_ = (int)(sample_rate * 0.375);
        delay_feedback_ = 0.5f;

        reverb_len_ = sample_rate * 3; // 3 seconds
        reverb_buffer_.resize(reverb_len_ * 2, 0.0f);
        reverb_write_pos_ = 0;
        reverb_feedback_ = 0.8f;
    }

    ~CppAudioEngine() {
        stop();
        Pa_Terminate();
    }

    void load_sample(int pad_id, py::array_t<float> data) {
        py::buffer_info buf = data.request();
        float* ptr = static_cast<float*>(buf.ptr);
        size_t size = buf.size; // Total number of floats
        
        // Assume stereo (interleaved) or mono. 
        // If 2D array (N, 2), size is N*2.
        
        std::lock_guard<std::mutex> lock(mutex_);
        samples_[pad_id] = std::vector<float>(ptr, ptr + size);
    }

    void play_sound(int pad_id, float velocity, float reverb, float delay, float start_offset_seconds) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (samples_.find(pad_id) == samples_.end()) return;
        
        int delay_frames = (int)(start_offset_seconds * sample_rate_);
        pending_voices_.push_back({pad_id, 0, velocity, reverb, delay, true, delay_frames});
    }

    void start() {
        if (stream_) return;

        Pa_OpenDefaultStream(&stream_,
                             0,          // no input channels
                             2,          // stereo output
                             paFloat32,  // 32-bit floating point output
                             sample_rate_,
                             256,        // frames per buffer (low latency)
                             &CppAudioEngine::paCallback,
                             this);

        Pa_StartStream(stream_);
    }

    void stop() {
        if (stream_) {
            Pa_StopStream(stream_);
            Pa_CloseStream(stream_);
            stream_ = nullptr;
        }
    }

    // PortAudio Callback
    static int paCallback(const void *inputBuffer, void *outputBuffer,
                          unsigned long framesPerBuffer,
                          const PaStreamCallbackTimeInfo* timeInfo,
                          PaStreamCallbackFlags statusFlags,
                          void *userData) {
        CppAudioEngine* engine = static_cast<CppAudioEngine*>(userData);
        return engine->process(static_cast<float*>(outputBuffer), framesPerBuffer);
    }

    int process(float* out, unsigned long frames) {
        // Clear output buffer
        std::fill(out, out + frames * 2, 0.0f);

        // Move pending voices to active voices
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (!pending_voices_.empty()) {
                voices_.insert(voices_.end(), pending_voices_.begin(), pending_voices_.end());
                pending_voices_.clear();
            }
        }
        
        // Reset mix buffers
        static float mix_l[1024];
        static float mix_r[1024];
        static float rev_l[1024];
        static float rev_r[1024];
        static float dly_l[1024];
        static float dly_r[1024];
        
        unsigned long safe_frames = (frames > 1024) ? 1024 : frames;
        
        std::fill(mix_l, mix_l + safe_frames, 0.0f);
        std::fill(mix_r, mix_r + safe_frames, 0.0f);
        std::fill(rev_l, rev_l + safe_frames, 0.0f);
        std::fill(rev_r, rev_r + safe_frames, 0.0f);
        std::fill(dly_l, dly_l + safe_frames, 0.0f);
        std::fill(dly_r, dly_r + safe_frames, 0.0f);

        for (auto& voice : voices_) {
            if (!voice.active) continue;
            
            // Handle start delay
            if (voice.start_delay_frames > 0) {
                if (voice.start_delay_frames >= (int)safe_frames) {
                    voice.start_delay_frames -= safe_frames;
                    continue; // Skip this entire block
                }
                // Partial delay handled below
            }

            auto& sample = samples_[voice.pad_id];
            size_t sample_len = sample.size();
            
            unsigned long start_idx = 0;
            if (voice.start_delay_frames > 0) {
                start_idx = voice.start_delay_frames;
                voice.start_delay_frames = 0;
            }

            for (unsigned long i = start_idx; i < safe_frames; ++i) {
                if (voice.pos >= sample_len - 1) {
                    voice.active = false;
                    break;
                }
                
                float s_l = sample[voice.pos];
                float s_r = sample[voice.pos+1];
                
                float v = voice.velocity;
                
                mix_l[i] += s_l * v;
                mix_r[i] += s_r * v;
                
                rev_l[i] += s_l * v * voice.reverb_send;
                rev_r[i] += s_r * v * voice.reverb_send;
                
                dly_l[i] += s_l * v * voice.delay_send;
                dly_r[i] += s_r * v * voice.delay_send;
                
                voice.pos += 2;
            }
        }
        
        voices_.erase(std::remove_if(voices_.begin(), voices_.end(), 
            [](const Voice& v){ return !v.active; }), voices_.end());

        // Apply Effects (Delay)
        for (unsigned long i = 0; i < safe_frames; ++i) {
            // Read Delay
            int read_pos = (delay_write_pos_ - delay_time_samples_ + delay_len_) % delay_len_;
            float d_l = delay_buffer_[read_pos * 2];
            float d_r = delay_buffer_[read_pos * 2 + 1];
            
            // Write Delay
            float in_l = dly_l[i] + d_l * delay_feedback_;
            float in_r = dly_r[i] + d_r * delay_feedback_;
            
            delay_buffer_[delay_write_pos_ * 2] = in_l;
            delay_buffer_[delay_write_pos_ * 2 + 1] = in_r;
            
            delay_write_pos_ = (delay_write_pos_ + 1) % delay_len_;
            
            // Add to mix
            mix_l[i] += d_l;
            mix_r[i] += d_r;
        }

        // Apply Effects (Reverb)
        for (unsigned long i = 0; i < safe_frames; ++i) {
            int read_pos = (reverb_write_pos_ - (int)(sample_rate_ * 0.1) + reverb_len_) % reverb_len_;
            float r_l = reverb_buffer_[read_pos * 2];
            float r_r = reverb_buffer_[read_pos * 2 + 1];
            
            float in_l = rev_l[i] + r_l * reverb_feedback_;
            float in_r = rev_r[i] + r_r * reverb_feedback_;
            
            reverb_buffer_[reverb_write_pos_ * 2] = in_l;
            reverb_buffer_[reverb_write_pos_ * 2 + 1] = in_r;
            
            reverb_write_pos_ = (reverb_write_pos_ + 1) % reverb_len_;
            
            mix_l[i] += r_l * 0.5f;
            mix_r[i] += r_r * 0.5f;
        }

        // Interleave to output with Soft Clipping
        for (unsigned long i = 0; i < safe_frames; ++i) {
            out[i*2] = std::tanh(mix_l[i]);
            out[i*2+1] = std::tanh(mix_r[i]);
        }

        return paContinue;
    }

private:
    int sample_rate_;
    PaStream* stream_;
    std::mutex mutex_;
    
    std::map<int, std::vector<float>> samples_;
    std::vector<Voice> voices_;
    std::vector<Voice> pending_voices_;
    
    // Delay
    std::vector<float> delay_buffer_;
    int delay_len_;
    int delay_write_pos_;
    int delay_time_samples_;
    float delay_feedback_;
    
    // Reverb
    std::vector<float> reverb_buffer_;
    int reverb_len_;
    int reverb_write_pos_;
    float reverb_feedback_;
};

PYBIND11_MODULE(groovebox_audio_cpp, m) {
    py::class_<CppAudioEngine>(m, "CppAudioEngine")
        .def(py::init<int>(), py::arg("sample_rate") = 44100)
        .def("start", &CppAudioEngine::start)
        .def("stop", &CppAudioEngine::stop)
        .def("load_sample", &CppAudioEngine::load_sample)
        .def("play_sound", &CppAudioEngine::play_sound, 
             py::arg("pad_id"), py::arg("velocity"), py::arg("reverb"), py::arg("delay"), py::arg("start_offset_seconds") = 0.0f);
}
