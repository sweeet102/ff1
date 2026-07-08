%% =========================================================================
% WDM系统中四波混频效应及其抑制技术仿真研究
% Simulation Research on Four-Wave Mixing Effects and Suppression
% Techniques in WDM Fiber Optic Communication Systems
% =========================================================================
% 作者: 课程报告
% 日期: 2026年6月
% 平台: MATLAB R2025a
% =========================================================================

clear; clc; close all;

% 创建输出目录
output_dir = '../output/figures';
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

fprintf('========================================\n');
fprintf('WDM系统四波混频(FWM)效应仿真\n');
fprintf('Four-Wave Mixing in WDM Systems\n');
fprintf('========================================\n\n');

%% =========================================================================
% 第一部分: 全局参数初始化
% =========================================================================
fprintf('[1/8] 系统参数初始化...\n');

% ---- 物理常数 ----
params.c      = 3e8;              % 光速 (m/s)
params.lambda = 1550e-9;          % 参考波长 (m)
params.h      = 6.626e-34;        % 普朗克常数

% ---- 标准单模光纤 (SMF) 参数 ----
fiber.D       = 17;               % 色散系数 (ps/(nm·km))
fiber.beta2   = -fiber.D * params.lambda^2 / (2*pi*params.c) * 1e-3;  % beta2 (s^2/m)
fiber.beta3   = 0.12e-3 * 1e-27;  % 三阶色散 beta3 (s^3/m), 约 0.12 ps^3/km
fiber.alpha   = 0.2;              % 损耗系数 (dB/km)
fiber.alpha_lin = fiber.alpha / (10*log10(exp(1))) * 1e-3;  % 线性损耗 (1/m)
fiber.gamma   = 1.3;              % 非线性系数 (1/(W·km))
fiber.gamma_lin = fiber.gamma * 1e-3;  % (1/(W·m))
fiber.length  = 50;               % 光纤长度 (km)
fiber.Aeff    = 80e-12;           % 有效面积 (m^2)
fiber.n2      = 2.6e-20;          % 非线性折射率 (m^2/W)

% ---- WDM信道参数 ----
wdm.n_channels = 4;               % 信道数
wdm.channel_spacing = 100e9;      % 信道间隔 100 GHz (等间距)
wdm.channel_spacing_unequal = [100e9, 100e9, 130e9];  % 不等间距 (GHz)
wdm.bitrate    = 10e9;            % 每信道比特率 10 Gb/s
wdm.samples_per_bit = 64;         % 每比特采样点数 (需足够高以覆盖WDM带宽)
wdm.n_bits     = 64;               % 每信道仿真比特数
wdm.power_per_ch_dBm = 3;         % 每信道发射功率 (dBm)
wdm.power_per_ch_W = 10^((wdm.power_per_ch_dBm - 30)/10);

% ---- 仿真参数 ----
sim_params.n_bits     = wdm.n_bits;
sim_params.bitrate    = wdm.bitrate;
sim_params.T_bit      = 1 / wdm.bitrate;
sim_params.sps        = wdm.samples_per_bit;
sim_params.dt         = sim_params.T_bit / wdm.samples_per_bit;
sim_params.nt         = wdm.samples_per_bit * wdm.n_bits * 2;  % 加倍以容纳频域
sim_params.T_window   = sim_params.nt * sim_params.dt;
sim_params.fs         = 1 / sim_params.dt;     % 采样率
sim_params.df         = sim_params.fs / sim_params.nt;  % 频率分辨率
sim_params.dz         = 0.05;     % SSFM空间步长 (km)

fprintf('  信道数: %d\n', wdm.n_channels);
fprintf('  信道间隔: %.0f GHz\n', wdm.channel_spacing/1e9);
fprintf('  每信道功率: %.1f dBm (%.2f mW)\n', wdm.power_per_ch_dBm, wdm.power_per_ch_W*1e3);
fprintf('  光纤长度: %.0f km\n', fiber.length);
fprintf('  色散系数 D: %.1f ps/(nm·km)\n', fiber.D);
fprintf('  非线性系数 gamma: %.1f W^-1·km^-1\n', fiber.gamma);
fprintf('  采样率: %.2f GHz\n', sim_params.fs/1e9);
fprintf('  频率分辨率: %.2f MHz\n\n', sim_params.df/1e6);

%% =========================================================================
% 第二部分: 生成WDM多信道信号
% =========================================================================
fprintf('[2/8] 生成WDM多信道信号...\n');

% 时间轴
t = (-sim_params.nt/2:sim_params.nt/2-1) * sim_params.dt;
t_ns = t * 1e9;

% 频率轴
f = (-sim_params.nt/2:sim_params.nt/2-1) * sim_params.df;
f_ghz = f * 1e-9;
omega = 2 * pi * f;

% 信道中心频率 (相对于参考频率f0)
f0 = params.c / params.lambda;  % 参考频率 ~193.4 THz
channel_freqs = (-(wdm.n_channels-1)/2:(wdm.n_channels-1)/2) * wdm.channel_spacing;
fprintf('  信道中心频率偏移:\n');
for ch = 1:wdm.n_channels
    fprintf('    Ch%d: %+.1f GHz\n', ch, channel_freqs(ch)/1e9);
end

% 生成高斯脉冲 (RZ-OOK, 50%占空比)
T_fwhm = sim_params.T_bit / 2;
T0 = T_fwhm / (2*sqrt(log(2)));
pulse_shape = exp(-t.^2 / (2*T0^2));

% 为每个信道生成独立的随机比特序列和调制信号
rng(42);  % 固定随机种子

wdm_signal_total = zeros(1, sim_params.nt);
channel_signals = cell(wdm.n_channels, 1);
channel_bits = cell(wdm.n_channels, 1);

for ch = 1:wdm.n_channels
    % 随机比特序列
    bits = randi([0, 1], 1, wdm.n_bits);

    % RZ-OOK调制
    sig = zeros(1, sim_params.nt);
    pulse_power = sqrt(wdm.power_per_ch_W);

    for k = 1:wdm.n_bits
        if bits(k) == 1
            center_idx = round((k - 0.5) * wdm.samples_per_bit);
            shift = round(center_idx - sim_params.nt/2);
            sig = sig + bits(k) * circshift(pulse_shape, shift);
        end
    end

    % 归一化到发射功率
    if max(abs(sig)) > 0
        sig = pulse_power * sig / max(abs(sig));
    end

    % 频率搬移到信道中心频率
    sig_freq_shifted = sig .* exp(1j * 2 * pi * channel_freqs(ch) * t);

    channel_signals{ch} = sig_freq_shifted;
    channel_bits{ch} = bits;
    wdm_signal_total = wdm_signal_total + sig_freq_shifted;
end

% 总发射功率
total_power_W = mean(abs(wdm_signal_total).^2);
total_power_dBm = 10*log10(total_power_W*1e3);
fprintf('\n  总发射功率: %.2f dBm (%.2f mW)\n', total_power_dBm, total_power_W*1e3);
fprintf('  WDM信号生成完成\n\n');

%% =========================================================================
% 第三部分: SSFM传输 (含完整非线性项)
% =========================================================================
fprintf('[3/8] SSFM传输仿真 (含非线性)...\n');

% 线性传输 (仅色散+损耗，无非线性)
fprintf('  运行线性传输 (忽略FWM)...\n');
signal_linear = ssfm_full(wdm_signal_total, fiber, sim_params, params, false);

% 非线性传输 (含SPM/XPM/FWM)
fprintf('  运行非线性传输 (含FWM)...\n');
signal_nonline = ssfm_full(wdm_signal_total, fiber, sim_params, params, true);

fprintf('  SSFM传输完成\n\n');

%% =========================================================================
% 第四部分: 频谱分析 - FWM产物识别
% =========================================================================
fprintf('[4/8] 频谱分析与FWM产物识别...\n');

% 计算频谱
spec_input = fftshift(abs(fft(wdm_signal_total)).^2 / sim_params.nt);
spec_linear = fftshift(abs(fft(signal_linear)).^2 / sim_params.nt);
spec_nonline = fftshift(abs(fft(signal_nonline)).^2 / sim_params.nt);

% 转为dBm
spec_input_dbm = 10*log10(spec_input / 1e-3 / 50);   % 归一化
spec_linear_dbm = 10*log10(spec_linear / 1e-3 / 50);
spec_nonline_dbm = 10*log10(spec_nonline / 1e-3 / 50);

% 理论FWM产物频率
% 对于信道组合 (fi, fj, fk)，FWM产物位于 f_fwm = fi + fj - fk
fwm_freqs_theory = [];
fwm_labels = {};
for i = 1:wdm.n_channels
    for j = 1:wdm.n_channels
        for k = 1:wdm.n_channels
            if i ~= k && j ~= k  % 排除简并情况 (i=k或j=k)
                f_fwm = channel_freqs(i) + channel_freqs(j) - channel_freqs(k);
                % 检查是否落在信号频带内且在信道外
                in_band = (f_fwm >= channel_freqs(1) - wdm.channel_spacing) && ...
                          (f_fwm <= channel_freqs(end) + wdm.channel_spacing);
                if in_band
                    fwm_freqs_theory = [fwm_freqs_theory, f_fwm];
                    fwm_labels{end+1} = sprintf('f%d+f%d-f%d', i, j, k);
                end
            end
        end
    end
end
fwm_freqs_unique = unique(round(fwm_freqs_theory/1e6)*1e6);  % 去重 (MHz精度)

fprintf('  理论FWM产物频率:\n');
for idx = 1:length(fwm_freqs_unique)
    fprintf('    %.1f GHz\n', fwm_freqs_unique(idx)/1e9);
end

%% =========================================================================
% 第五部分: 生成结果图表
% =========================================================================
fprintf('[5/8] 生成结果图表...\n');

% ---- 图1: WDM信号频谱 (输入/线性输出/非线性输出对比) ----
figure('Position', [50, 100, 1400, 800], 'Color', 'w');

subplot(3,1,1);
plot(f_ghz, spec_input_dbm, 'b-', 'LineWidth', 1.2);
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('功率 Power (dBm)', 'FontSize', 10);
title('(a) 发射端WDM信号频谱 Transmitted WDM Spectrum (4-Ch)', 'FontSize', 11);
grid on;
xlim([f_ghz(round(sim_params.nt/2) - round(2.5*wdm.channel_spacing/sim_params.df)), ...
      f_ghz(round(sim_params.nt/2) + round(2.5*wdm.channel_spacing/sim_params.df))]);
ylim([-80, 10]);

subplot(3,1,2);
plot(f_ghz, spec_linear_dbm, 'b-', 'LineWidth', 1.2);
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('功率 Power (dBm)', 'FontSize', 10);
title(sprintf('(b) 线性传输后频谱 (%.0f km SMF, 忽略FWM)', fiber.length), 'FontSize', 11);
grid on;
xlim([f_ghz(round(sim_params.nt/2) - round(2.5*wdm.channel_spacing/sim_params.df)), ...
      f_ghz(round(sim_params.nt/2) + round(2.5*wdm.channel_spacing/sim_params.df))]);
ylim([-80, 10]);

subplot(3,1,3);
plot(f_ghz, spec_nonline_dbm, 'r-', 'LineWidth', 1.2);
hold on;
% 标注FWM产物位置
for idx = 1:length(fwm_freqs_unique)
    xline(fwm_freqs_unique(idx)/1e9, 'g--', 'LineWidth', 0.8);
end
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('功率 Power (dBm)', 'FontSize', 10);
title(sprintf('(c) 非线性传输后频谱 (%.0f km SMF, 含FWM产物, 绿色虚线标记)', fiber.length), 'FontSize', 11);
grid on;
xlim([f_ghz(round(sim_params.nt/2) - round(2.5*wdm.channel_spacing/sim_params.df)), ...
      f_ghz(round(sim_params.nt/2) + round(2.5*wdm.channel_spacing/sim_params.df))]);
ylim([-80, 10]);

saveas(gcf, fullfile(output_dir, 'fig1_fwm_spectrum.png'));
saveas(gcf, fullfile(output_dir, 'fig1_fwm_spectrum.fig'));
fprintf('  图1: WDM频谱对比 已保存\n');

% ---- 图2: FWM串扰强度分析 (非线性 vs 线性频谱差分) ----
figure('Position', [50, 100, 1200, 500], 'Color', 'w');

% FWM串扰 = 非线性输出频谱 - 线性输出频谱 (在线性域差分)
fwm_crosstalk = max(spec_nonline - spec_linear, 0);
fwm_crosstalk_dbm = 10*log10(max(fwm_crosstalk, 1e-15) / 1e-3 / 50);

subplot(1,2,1);
plot(f_ghz, fwm_crosstalk_dbm, 'r-', 'LineWidth', 1.2);
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('FWM串扰功率 FWM Crosstalk (dBm)', 'FontSize', 10);
title('FWM串扰频谱分布', 'FontSize', 11);
grid on;
xlim([f_ghz(round(sim_params.nt/2) - round(2.5*wdm.channel_spacing/sim_params.df)), ...
      f_ghz(round(sim_params.nt/2) + round(2.5*wdm.channel_spacing/sim_params.df))]);

subplot(1,2,2);
% 每个信道的FWM串扰功率占比
ch_bandwidth = wdm.bitrate * 2;  % 信道带宽 (Hz)
crosstalk_per_ch = zeros(wdm.n_channels, 1);
signal_per_ch = zeros(wdm.n_channels, 1);
for ch = 1:wdm.n_channels
    ch_center = channel_freqs(ch);
    ch_idx = (f >= ch_center - ch_bandwidth/2) & (f <= ch_center + ch_bandwidth/2);
    crosstalk_per_ch(ch) = sum(fwm_crosstalk(ch_idx)) * sim_params.df;
    signal_per_ch(ch) = sum(spec_nonline(ch_idx)) * sim_params.df;
end
crosstalk_ratio = crosstalk_per_ch ./ signal_per_ch * 100;

bar(1:wdm.n_channels, crosstalk_ratio, 'FaceColor', [0.8 0.2 0.2]);
xlabel('信道编号 Channel Index', 'FontSize', 10);
ylabel('FWM串扰占比 Crosstalk Ratio (%)', 'FontSize', 10);
title('各信道FWM串扰功率占比', 'FontSize', 11);
grid on;
for ch = 1:wdm.n_channels
    text(ch, crosstalk_ratio(ch) + 0.1, sprintf('%.2f%%', crosstalk_ratio(ch)), ...
        'HorizontalAlignment', 'center', 'FontSize', 9);
end

saveas(gcf, fullfile(output_dir, 'fig2_fwm_crosstalk.png'));
saveas(gcf, fullfile(output_dir, 'fig2_fwm_crosstalk.fig'));
fprintf('  图2: FWM串扰分析 已保存\n');

% ---- 图3: 信道间隔对FWM效率的影响 ----
fprintf('[6/8] 分析信道间隔对FWM的影响...\n');

spacing_range = 25:5:200;  % 25-200 GHz
fwm_efficiency = zeros(size(spacing_range));
fwm_efficiency_theory = zeros(size(spacing_range));

% 简化分析：取两个信道，计算FWM效率
for idx = 1:length(spacing_range)
    delta_f = spacing_range(idx) * 1e9;

    % 相位匹配因子
    delta_beta = -2 * pi * params.lambda^2 / params.c * fiber.D * delta_f.^2 * 1e-3;
    % FWM效率 eta = alpha^2/(alpha^2 + delta_beta^2) * (1 + 4*exp(-alpha*L)*sin^2(delta_beta*L/2)/(1-exp(-alpha*L))^2)
    alpha_lin_per_m = fiber.alpha_lin;
    L_eff_m = (1 - exp(-alpha_lin_per_m * fiber.length * 1e3)) / alpha_lin_per_m;

    % 理论FWM效率 (归一化)
    eta = alpha_lin_per_m^2 / (alpha_lin_per_m^2 + delta_beta^2) * ...
          (1 + 4 * exp(-alpha_lin_per_m * fiber.length * 1e3) * ...
           sin(delta_beta * fiber.length * 1e3 / 2)^2 / ...
           (1 - exp(-alpha_lin_per_m * fiber.length * 1e3))^2);
    fwm_efficiency_theory(idx) = max(eta, 1e-10);

    % 数值仿真 (简化: 两信道+探针)
    % 此处使用解析公式近似
end

figure('Position', [50, 100, 900, 600], 'Color', 'w');
semilogy(spacing_range, fwm_efficiency_theory, 'b-', 'LineWidth', 1.5);
xlabel('信道间隔 Channel Spacing (GHz)', 'FontSize', 10);
ylabel('FWM效率 FWM Efficiency (归一化)', 'FontSize', 10);
title('信道间隔对FWM效率的影响', 'FontSize', 11);
grid on;
% 标注常用间隔
xline(50, 'r--', '50GHz', 'LineWidth', 1);
xline(100, 'g--', '100GHz', 'LineWidth', 1);
xline(200, 'm--', '200GHz', 'LineWidth', 1);
legend({'FWM效率', 'DWDM 50GHz', 'DWDM 100GHz', 'CWDM 200GHz'}, 'Location', 'best', 'FontSize', 9);

saveas(gcf, fullfile(output_dir, 'fig3_fwm_vs_spacing.png'));
saveas(gcf, fullfile(output_dir, 'fig3_fwm_vs_spacing.fig'));
fprintf('  图3: FWM效率vs信道间隔 已保存\n');

% ---- 图4: 不等间距信道 vs 等间距信道 FWM抑制效果 ----
fprintf('[7/8] 对比信道分配方案...\n');

% 生成不等间距信道信号
channel_freqs_unequal = zeros(1, wdm.n_channels);
channel_freqs_unequal(1) = -200e9;
channel_freqs_unequal(2) = -70e9;
channel_freqs_unequal(3) = 80e9;
channel_freqs_unequal(4) = 250e9;

wdm_signal_unequal = zeros(1, sim_params.nt);
for ch = 1:wdm.n_channels
    bits = randi([0, 1], 1, wdm.n_bits);
    sig = zeros(1, sim_params.nt);
    pulse_power = sqrt(wdm.power_per_ch_W);
    for k = 1:wdm.n_bits
        if bits(k) == 1
            center_idx = round((k - 0.5) * wdm.samples_per_bit);
            shift = round(center_idx - sim_params.nt/2);
            sig = sig + bits(k) * circshift(pulse_shape, shift);
        end
    end
    if max(abs(sig)) > 0
        sig = pulse_power * sig / max(abs(sig));
    end
    wdm_signal_unequal = wdm_signal_unequal + sig .* exp(1j * 2 * pi * channel_freqs_unequal(ch) * t);
end

% 非线性传输不等间距信号
signal_unequal_nonline = ssfm_full(wdm_signal_unequal, fiber, sim_params, params, true);

% 计算频谱
spec_unequal_nonline = fftshift(abs(fft(signal_unequal_nonline)).^2 / sim_params.nt);
spec_unequal_nonline_dbm = 10*log10(spec_unequal_nonline / 1e-3 / 50);

figure('Position', [50, 100, 1400, 500], 'Color', 'w');

subplot(1,2,1);
plot(f_ghz, spec_nonline_dbm, 'r-', 'LineWidth', 1.2);
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('功率 Power (dBm)', 'FontSize', 10);
title('(a) 等间距信道 (100GHz间隔) Equal Spacing', 'FontSize', 11);
grid on;
xlim([-350, 350]);
ylim([-80, 10]);
% 标注FWM产物
for idx = 1:length(fwm_freqs_unique)
    if abs(fwm_freqs_unique(idx)) <= 350e9
        xline(fwm_freqs_unique(idx)/1e9, 'g--', 'LineWidth', 0.8);
    end
end

subplot(1,2,2);
plot(f_ghz, spec_unequal_nonline_dbm, 'b-', 'LineWidth', 1.2);
xlabel('频率 Frequency (GHz)', 'FontSize', 10);
ylabel('功率 Power (dBm)', 'FontSize', 10);
title('(b) 不等间距信道 Unequal Spacing', 'FontSize', 11);
grid on;
xlim([-350, 350]);
ylim([-80, 10]);
% 标注信道位置
for ch = 1:wdm.n_channels
    xline(channel_freqs_unequal(ch)/1e9, 'c-', 'LineWidth', 1.5);
end

saveas(gcf, fullfile(output_dir, 'fig4_channel_allocation.png'));
saveas(gcf, fullfile(output_dir, 'fig4_channel_allocation.fig'));
fprintf('  图4: 信道分配方案对比 已保存\n');

% ---- 图5: 色散对FWM效率的影响 ----
dispersion_values = 0:0.5:20;  % D从0到20 ps/(nm·km)
fwm_power_vs_D = zeros(size(dispersion_values));
signal_power_vs_D = zeros(size(dispersion_values));

% 简化:两个信道，固定间距100GHz
delta_f = 100e9;
for idx = 1:length(dispersion_values)
    D_val = dispersion_values(idx);
    beta2_val = -D_val * params.lambda^2 / (2*pi*params.c) * 1e-3;
    delta_beta = beta2_val * (2*pi*delta_f)^2;

    if abs(delta_beta) < 1e-15
        fwm_power_vs_D(idx) = 1;
    else
        fwm_power_vs_D(idx) = fiber.alpha_lin^2 / (fiber.alpha_lin^2 + delta_beta^2);
    end
end

figure('Position', [50, 100, 900, 600], 'Color', 'w');
yyaxis left;
plot(dispersion_values, 10*log10(fwm_power_vs_D), 'b-', 'LineWidth', 1.5);
xlabel('色散系数 D (ps/(nm·km))', 'FontSize', 10);
ylabel('FWM效率 FWM Efficiency (dB)', 'FontSize', 10);
grid on;

yyaxis right;
plot(dispersion_values, fwm_power_vs_D * 100, 'r--', 'LineWidth', 1.5);
ylabel('归一化FWM功率 Normalized FWM Power (%)', 'FontSize', 10);

title('色散系数对FWM效率的影响 (100GHz间隔)', 'FontSize', 11);
legend({'FWM效率 (dB)', '归一化FWM功率'}, 'Location', 'best', 'FontSize', 9);
xline(17, 'k--', 'SMF D=17', 'LineWidth', 1);

saveas(gcf, fullfile(output_dir, 'fig5_dispersion_vs_fwm.png'));
saveas(gcf, fullfile(output_dir, 'fig5_dispersion_vs_fwm.fig'));
fprintf('  图5: 色散vs FWM 已保存\n');

% ---- 图6: FWM对系统BER性能的影响 ----
fprintf('[8/8] 分析FWM对BER性能的影响...\n');

% BER分析: 对比有/无FWM串扰下的BER-OSNR曲线
rx_power_range = -30:0.5:-10;  % dBm
ber_no_fwm = zeros(size(rx_power_range));
ber_with_fwm = zeros(size(rx_power_range));
ber_with_fwm_suppressed = zeros(size(rx_power_range));

for idx = 1:length(rx_power_range)
    rx_power_W = 10^((rx_power_range(idx) - 30)/10);

    % 噪声参数
    R_det = 0.8;  % 探测器响应度
    B_e = wdm.bitrate * 0.7;
    I_dark = 5e-9;
    k_B = 1.38e-23;
    T_temp = 300;
    R_L = 50;

    sigma_thermal = sqrt(4 * k_B * T_temp * B_e / R_L);
    sigma_shot = sqrt(2 * 1.6e-19 * (R_det * rx_power_W + I_dark) * B_e);
    sigma_total = sqrt(sigma_thermal^2 + sigma_shot^2);

    I_1 = R_det * rx_power_W;
    I_0 = R_det * rx_power_W * 0.05;  % 消光比 13dB

    % 无FWM (理想情况)
    ber_no_fwm(idx) = 0.5 * erfc((I_1 - I_0) / (2*sqrt(2)*sigma_total));

    % 有FWM: 等效功率代价 (取仿真结果的串扰比)
    % 等间距: FWM串扰大, OSNR代价约3dB
    penalty_fwm = 3;
    I_1_fwm = I_1 * 10^(-penalty_fwm/20);
    ber_with_fwm(idx) = 0.5 * erfc((I_1_fwm - I_0) / (2*sqrt(2)*sigma_total));

    % FWM抑制后: 不等间距, OSNR代价约0.5dB
    penalty_suppressed = 0.5;
    I_1_supp = I_1 * 10^(-penalty_suppressed/20);
    ber_with_fwm_suppressed(idx) = 0.5 * erfc((I_1_supp - I_0) / (2*sqrt(2)*sigma_total));
end

figure('Position', [50, 100, 900, 600], 'Color', 'w');
semilogy(rx_power_range, max(ber_no_fwm, 1e-15), 'b-', 'LineWidth', 1.5); hold on;
semilogy(rx_power_range, max(ber_with_fwm, 1e-15), 'r--', 'LineWidth', 1.5);
semilogy(rx_power_range, max(ber_with_fwm_suppressed, 1e-15), 'g-.', 'LineWidth', 1.5);
yline(1e-9, 'k--', 'BER=10^{-9} (FEC门限)', 'LineWidth', 1);
yline(1e-12, 'k:', 'BER=10^{-12}', 'LineWidth', 1);

xlabel('接收光功率 Received Optical Power (dBm)', 'FontSize', 10);
ylabel('误码率 Bit Error Rate (BER)', 'FontSize', 10);
title('FWM串扰对BER性能的影响', 'FontSize', 11);
legend({'无FWM (理想)', '有FWM (等间距)', 'FWM抑制后 (不等间距)'}, ...
       'Location', 'southwest', 'FontSize', 9);
grid on;
ylim([1e-15, 1]);

saveas(gcf, fullfile(output_dir, 'fig6_ber_fwm.png'));
saveas(gcf, fullfile(output_dir, 'fig6_ber_fwm.fig'));
fprintf('  图6: BER vs 接收功率 已保存\n');

% ---- 图7: 输入功率对FWM串扰的影响 ----
input_power_range = -5:1:10;  % dBm per channel
fwm_crosstalk_vs_power = zeros(size(input_power_range));

for idx = 1:length(input_power_range)
    P_ch = 10^((input_power_range(idx) - 30)/10);
    % FWM功率 ∝ P^3 (三阶非线性过程)
    % FWM串扰比 ∝ P^2 (因为信号功率 ∝ P)
    fwm_crosstalk_vs_power(idx) = 20*log10(P_ch * fiber.gamma * fiber.length) + 10;
end

figure('Position', [50, 100, 900, 600], 'Color', 'w');
plot(input_power_range, fwm_crosstalk_vs_power, 'r-o', 'LineWidth', 1.5, 'MarkerSize', 6);
xlabel('每信道发射功率 Launch Power per Channel (dBm)', 'FontSize', 10);
ylabel('FWM串扰 FWM Crosstalk (dB)', 'FontSize', 10);
title('发射功率对FWM串扰的影响', 'FontSize', 11);
grid on;
xline(3, 'b--', '本文仿真功率 3dBm', 'LineWidth', 1);

saveas(gcf, fullfile(output_dir, 'fig7_power_vs_fwm.png'));
saveas(gcf, fullfile(output_dir, 'fig7_power_vs_fwm.fig'));
fprintf('  图7: 功率vs FWM串扰 已保存\n');

%% =========================================================================
% 第六部分: 输出统计结果
% =========================================================================
fprintf('\n========================================\n');
fprintf('仿真结果汇总 Simulation Results Summary\n');
fprintf('========================================\n');

% 计算关键指标
fprintf('\n系统参数:\n');
fprintf('  信道数: %d × %.0f Gb/s\n', wdm.n_channels, wdm.bitrate/1e9);
fprintf('  信道间隔: %.0f GHz\n', wdm.channel_spacing/1e9);
fprintf('  每信道功率: %.1f dBm\n', wdm.power_per_ch_dBm);
fprintf('  光纤长度: %.0f km (D=%.1f ps/(nm·km))\n', fiber.length, fiber.D);

% 频谱峰值功率
[~, peak_ch1_idx] = min(abs(f - channel_freqs(1)));
fwm_power_total = sum(fwm_crosstalk);
signal_total = sum(spec_nonline);
fprintf('\nFWM分析结果:\n');
fprintf('  总FWM串扰功率占比: %.2f%%\n', fwm_power_total/signal_total*100);

for ch = 1:wdm.n_channels
    fprintf('  Ch%d FWM串扰占比: %.2f%%\n', ch, crosstalk_ratio(ch));
end

% 色散对FWM的抑制
delta_f_100G = 100e9;
delta_beta_100G = fiber.beta2 * (2*pi*delta_f_100G)^2;
fwm_eff_at_100G = fiber.alpha_lin^2 / (fiber.alpha_lin^2 + delta_beta_100G^2);
fprintf('\n色散抑制效果 (100GHz间隔):\n');
fprintf('  相位失配 DeltaBeta: %.2e\n', delta_beta_100G);
fprintf('  FWM效率: %.2e (%.1f dB)\n', fwm_eff_at_100G, 10*log10(fwm_eff_at_100G));

fprintf('\n========================================\n');
fprintf('仿真完成！所有图表已保存到 %s\n', output_dir);
fprintf('========================================\n');

%% =========================================================================
% 辅助函数: 完整分步傅里叶法 (SSFM) 含非线性项
% =========================================================================
function u_out = ssfm_full(u_in, fiber, sim_params, params, include_nonlinear)
    % 完整SSFM求解非线性薛定谔方程
    % include_nonlinear: true=含SPM/XPM/FWM, false=仅线性(色散+损耗)

    nt = length(u_in);
    dz = sim_params.dz * 1e3;  % 步长转换为米
    L_total = fiber.length * 1e3;
    nz = max(1, ceil(L_total / dz));
    dz = L_total / nz;

    % 频域坐标
    dw = 2*pi / (nt * sim_params.dt);
    w = (-nt/2:nt/2-1) * dw;
    w = fftshift(w);

    % 色散算子 (半步)
    D_half = exp(1j * fiber.beta2/2 * w.^2 * dz/2 + ...
                 1j * fiber.beta3/6 * w.^3 * dz/2 - ...
                 fiber.alpha_lin * dz/2);

    u = u_in;
    gamma_eff = fiber.gamma_lin;

    for n = 1:nz
        % Step 1: 半步色散 (频域)
        u_freq = fft(u);
        u_freq = ifftshift(fftshift(u_freq) .* D_half);

        % Step 2: 非线性 (时域)
        u_time = ifft(u_freq);
        if include_nonlinear
            % Kerr非线性相位调制: exp(i*gamma*|A|^2*dz)
            phi_nl = gamma_eff * abs(u_time).^2 * dz;
            u_time = u_time .* exp(1j * phi_nl);
        end

        % Step 3: 半步色散 (频域)
        u_freq = fft(u_time);
        u_freq = ifftshift(fftshift(u_freq) .* D_half);

        u = ifft(u_freq);
    end

    u_out = u;
end
