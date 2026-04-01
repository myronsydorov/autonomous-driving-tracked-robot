#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "sensor_msgs/msg/magnetic_field.hpp"

#include <sstream>
#include <iomanip>
#include <unistd.h>
#include <termios.h>
#include <errno.h>
#include <fcntl.h>
#include <iostream>
#include <time.h>
#include <arpa/inet.h>
#include <signal.h>

#include <Eigen/Core>
#include <Eigen/Dense>

using namespace std;
using namespace Eigen;

#define PI (3.1415926535898)
#define RAD2DEG (180.0 / PI)
#define DEG2RAD (PI / 180.0)

class VN100Publisher : public rclcpp::Node {
public:
    VN100Publisher()
    : Node("vn100_node") {
        this->declare_parameter<std::string>("device", "/dev/ttyUSB0");
        device_param = this->get_parameter("device");
        device_name = device_param.as_string();

        this->declare_parameter<int>("rate", 50);
        output_imu_rate_param = this->get_parameter("rate");
        rate = output_imu_rate_param.as_int();

        connect_imu();
        send_output_configuration();

        this->declare_parameter<std::string>("output_mag", "mag_meas");
        output_mag_param = this->get_parameter("output_mag");
        std::string parameter_string_mag = output_mag_param.as_string();
        mag_publisher = this->create_publisher<sensor_msgs::msg::MagneticField>(parameter_string_mag, 10);

        this->declare_parameter<std::string>("output_imu", "imu_meas");
        output_imu_param = this->get_parameter("output_imu");
        std::string parameter_string_imu = output_imu_param.as_string();
        imu_meas_publisher = this->create_publisher<sensor_msgs::msg::Imu>(parameter_string_imu, 10);

        flag = true;
        start();
        timer_ = this->create_wall_timer(100ms, std::bind(&VN100Publisher::timer_callback, this));
    }

private:
    std::thread* m_thread;
    rclcpp::Parameter device_param;
    rclcpp::Parameter output_imu_rate_param;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_meas_publisher;
    rclcpp::Publisher<sensor_msgs::msg::MagneticField>::SharedPtr mag_publisher;
    rclcpp::Parameter output_mag_param;
    rclcpp::Parameter output_imu_param;
    rclcpp::TimerBase::SharedPtr timer_;
    std::string device_name;
    rclcpp::Time time_tag;
    int32_t counter;
    uint8_t rate;
    uint8_t workbuf[1024];
    int32_t workbufIndex;
    int32_t workbufFSM;
    int fd_imu;
    struct termios options;
    bool flag;

public:
    ~VN100Publisher() {}

private:
    void connect_imu() {
        if ((fd_imu = open(device_name.c_str(), O_RDWR | O_NONBLOCK)) < 0) {
            std::cout << "Could not open device " << device_name << std::endl;
        } else {
            std::cout << "Successfully opened " << device_name << std::endl;
        }

        memset(&options, 0, sizeof(struct termios));
        tcgetattr(fd_imu, &options);
        options.c_iflag &= ~(IXON | IXOFF | IXANY);
        cfsetispeed(&options, B115200);
        cfsetospeed(&options, B115200);
        options.c_cflag |= (CREAD | CLOCAL);
        options.c_cflag |= CS8;
        options.c_cflag &= ~CRTSCTS;
        options.c_iflag &= ~(ICRNL);
        options.c_oflag &= ~(OPOST | ONLCR);
        options.c_lflag &= ~(ISIG | ICANON | IEXTEN | ECHO | ECHOE | ECHOK | ECHOCTL | ECHOKE);
        tcsetattr(fd_imu, TCSANOW, &options);
        tcsetattr(fd_imu, TCSAFLUSH, &options);

        workbufIndex = 0;
        workbufFSM = 0;
    }

    uint16_t calculateCRC(unsigned char data[], unsigned int length) {
        unsigned short crc = 0;
        for (unsigned int i = 0; i < length; i++) {
            crc = (unsigned char)(crc >> 8) | (crc << 8);
            crc ^= data[i];
            crc ^= (unsigned char)(crc & 0xff) >> 4;
            crc ^= crc << 12;
            crc ^= (crc & 0x00ff) << 5;
        }
        return crc;
    }

    void timer_callback() {}

    void my_delay(double ms) {
        struct timespec ts;
        int32_t seconds = floor(ms / 1000.0);
        double remainder = ms - seconds * 1000.0;
        double nanoseconds = ceil((remainder / 1000.0) * 1e9);
        ts.tv_sec = seconds;
        ts.tv_nsec = (int32_t)nanoseconds;
        nanosleep(&ts, NULL);
    }

    void start() {
        m_thread = new std::thread([this]() { process_data(); });
    }

    void process_data() {
        struct timespec ts;
        int n_bytes;
        uint8_t buf[1024];
        while (1) {
            n_bytes = read(fd_imu, buf, 1024);
            for (int ii = 0; ii < n_bytes; ii++) {
                process_serial_data(buf[ii]);
            }
            ts.tv_sec = 0;
            ts.tv_nsec = 1000L;
            nanosleep(&ts, NULL);
        }
    }

    void send_output_configuration() {
        std::string cmd;
        std::cout << "VN100: Rate = " << rate << std::endl;

        cmd = "$VNASY,0*XX\r\n";
        write(fd_imu, cmd.c_str(), cmd.length());
        my_delay(200);

        cmd = "$VNWRG,06,0*XX\r\n";
        write(fd_imu, cmd.c_str(), cmd.length());
        my_delay(200);

        if (rate == 50)
            cmd = "$VNWRG,75,2,16,01,0529*XX\r\n";
        else if (rate == 100)
            cmd = "$VNWRG,75,2,8,01,0529*XX\r\n";
        else
            cmd = "$VNWRG,75,2,16,01,0529*XX\r\n";
        write(fd_imu, cmd.c_str(), cmd.length());
        my_delay(200);

        cmd = "$VNASY,1*XX\r\n";
        write(fd_imu, cmd.c_str(), cmd.length());
        my_delay(200);
    }

    void process_serial_data(uint8_t buf) {
        switch (workbufFSM) {
            case 0:
                if (buf == 0xFA) {
                    workbufIndex = 0;
                    workbuf[workbufIndex++] = buf;
                    workbufFSM = 1;
                }
                break;
            case 1:
                if (buf == 0x01) {
                    workbuf[workbufIndex++] = buf;
                    workbufFSM = 2;
                } else workbufFSM = 0;
                break;
            case 2:
                if (buf == 0x29) {
                    workbuf[workbufIndex++] = buf;
                    workbufFSM = 3;
                } else workbufFSM = 0;
                break;
            case 3:
                if (buf == 0x05) {
                    workbuf[workbufIndex++] = buf;
                    workbufFSM = 4;
                } else workbufFSM = 0;
                break;
            case 4:
                workbuf[workbufIndex++] = buf;
                if (workbufIndex == 70) {
                    unsigned short computed_checksum = calculateCRC(&workbuf[1], 69);
                    if (computed_checksum == 0) {
                        time_tag = this->get_clock()->now();
                        process_data_output();
                    }
                    workbufFSM = 0;
                }
                break;
        }
    }

    void process_data_output() {
        sensor_msgs::msg::Imu imu_sample_meas;
        sensor_msgs::msg::MagneticField mag_meas;

        float roll, pitch, yaw;
        float accX, accY, accZ;
        float gyroX, gyroY, gyroZ;
        float magX, magY, magZ;
        float temperature, pressure;
        uint64_t time_startup;

        int32_t ind = 4;
        memcpy(&time_startup, &workbuf[ind], 8); ind += 8;
        memcpy(&yaw, &workbuf[ind], 4); ind += 4;
        memcpy(&pitch, &workbuf[ind], 4); ind += 4;
        memcpy(&roll, &workbuf[ind], 4); ind += 4;
        memcpy(&gyroX, &workbuf[ind], 4); ind += 4;
        memcpy(&gyroY, &workbuf[ind], 4); ind += 4;
        memcpy(&gyroZ, &workbuf[ind], 4); ind += 4;
        memcpy(&accX, &workbuf[ind], 4); ind += 4;
        memcpy(&accY, &workbuf[ind], 4); ind += 4;
        memcpy(&accZ, &workbuf[ind], 4); ind += 4;
        memcpy(&magX, &workbuf[ind], 4); ind += 4;
        memcpy(&magY, &workbuf[ind], 4); ind += 4;
        memcpy(&magZ, &workbuf[ind], 4); ind += 4;
        memcpy(&temperature, &workbuf[ind], 4); ind += 4;
        memcpy(&pressure, &workbuf[ind], 4); ind += 4;


        imu_sample_meas.header.stamp = time_tag;
        imu_sample_meas.header.frame_id = "imu_link";

        // ‹FIX› BEGIN NED→ENU conversion
        // convert raw Euler (deg) to radians
        double roll_ned  = roll  * DEG2RAD;
        double pitch_ned = pitch * DEG2RAD;
        double yaw_ned   = yaw   * DEG2RAD;

        // ROS ENU = (roll, –pitch, –yaw)
        double roll_enu  =  roll_ned;
        double pitch_enu = -pitch_ned;
        double yaw_enu   = -yaw_ned;

        // build quaternion from ENU angles
        double c1 = cos(roll_enu  / 2.0);
        double s1 = sin(roll_enu  / 2.0);
        double c2 = cos(pitch_enu / 2.0);
        double s2 = sin(pitch_enu / 2.0);
        double c3 = cos(yaw_enu   / 2.0);
        double s3 = sin(yaw_enu   / 2.0);

        imu_sample_meas.orientation.w = c1*c2*c3 + s1*s2*s3;
        imu_sample_meas.orientation.x = s1*c2*c3 - c1*s2*s3;
        imu_sample_meas.orientation.y = c1*s2*c3 + s1*c2*s3;
        imu_sample_meas.orientation.z = c1*c2*s3 - s1*s2*c3;

        // flip Y and Z on the raw rates & accels
        imu_sample_meas.angular_velocity.x    = gyroX;
        imu_sample_meas.angular_velocity.y    = -gyroY;
        imu_sample_meas.angular_velocity.z    = -gyroZ;

        imu_sample_meas.linear_acceleration.x = accX;
        imu_sample_meas.linear_acceleration.y = -accY;
        imu_sample_meas.linear_acceleration.z = -accZ;


        // imu_sample_meas.header.stamp = time_tag;
        // imu_sample_meas.header.frame_id = "imu_link";

        // double c1 = cos(roll * DEG2RAD / 2);
        // double s1 = sin(roll * DEG2RAD / 2);
        // double c2 = cos(pitch * DEG2RAD / 2);
        // double s2 = sin(pitch * DEG2RAD / 2);
        // double c3 = cos(yaw * DEG2RAD / 2);
        // double s3 = sin(yaw * DEG2RAD / 2);

        // double q0 = c1 * c2 * c3 + s1 * s2 * s3;
        // double q1 = s1 * c2 * c3 - c1 * s2 * s3;
        // double q2 = c1 * s2 * c3 + s1 * c2 * s3;
        // double q3 = c1 * c2 * s3 - s1 * s2 * c3;

        // imu_sample_meas.orientation.w = q0;
        // imu_sample_meas.orientation.x = q1;
        // imu_sample_meas.orientation.y = q2;
        // imu_sample_meas.orientation.z = q3;

        // imu_sample_meas.angular_velocity.x = gyroX;
        // imu_sample_meas.angular_velocity.y = gyroY;
        // imu_sample_meas.angular_velocity.z = gyroZ;

        // imu_sample_meas.linear_acceleration.x = accX;
        // imu_sample_meas.linear_acceleration.y = accY;
        // imu_sample_meas.linear_acceleration.z = accZ;

        imu_meas_publisher->publish(imu_sample_meas);

        mag_meas.header.stamp = time_tag;
        mag_meas.header.frame_id = "imu_link";
        mag_meas.magnetic_field.x = magX;
        mag_meas.magnetic_field.y = magY;
        mag_meas.magnetic_field.z = magZ;

        mag_publisher->publish(mag_meas);

        counter++;
        if ((counter % rate) == 0) {
            std::cout << "VN100 Time: " << time_startup << "; " << roll << ", " << pitch << ", " << yaw << std::endl;
        }
    }
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<VN100Publisher>());
    rclcpp::shutdown();
    return 0;
}
