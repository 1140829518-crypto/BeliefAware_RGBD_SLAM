/**
 * @file rgbd_tum.cc
 * @author guoqing (1337841346@qq.com)
 * @brief TUM RGBD 数据集上测试ORB-SLAM2
 * @version 0.1
 * @date 2019-02-16
 * 
 * @copyright Copyright (c) 2019
 * 
 */


/**
* This file is part of ORB-SLAM2.
*
* Copyright (C) 2014-2016 Raúl Mur-Artal <raulmur at unizar dot es> (University of Zaragoza)
* For more information see <https://github.com/raulmur/ORB_SLAM2>
*
* ORB-SLAM2 is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* ORB-SLAM2 is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with ORB-SLAM2. If not, see <http://www.gnu.org/licenses/>.
*/



#include<iostream>
#include<algorithm>
#include<fstream>
#include<chrono>
#include<unistd.h>
#include<opencv2/core/core.hpp>

#include <memory>//zt1

#include<System.h>

#include "Frame.h"//zt2 
#include "Object.h"//zt3
#include "SemanticConfig.h"
#include "ExperimentTiming.h"

//for socket//zt4
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <stdio.h>
#include <sys/un.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>

using namespace std;

static string JoinDatasetPath(const string &datasetPath, const string &imagePath)
{
    if(!imagePath.empty() && imagePath[0] == '/')
        return imagePath;

    return datasetPath + "/" + imagePath;
}

/**
 * @brief 加载图像
 * 
 * @param[in] strAssociationFilename    关联文件的访问路径
 * @param[out] vstrImageFilenamesRGB     彩色图像路径序列
 * @param[out] vstrImageFilenamesD       深度图像路径序列
 * @param[out] vTimestamps               时间戳
 */
void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps);
//zt5************
void LoadBoundingBox(const string& strPathToDetectionResult, vector<std::pair<vector<double>, int>>& detect_result);

void LoadBoundingBoxFromPython(const string& resultFromPython, std::pair<vector<double>, int>& detect_result);
void MakeDetect_result(vector<std::pair<vector<double>, int>>& detect_result, int sockfd);
//zt5************
int main(int argc, char **argv)
{
    if(argc != 5)
    {
        cerr << endl << "Usage: ./rgbd_tum path_to_vocabulary path_to_settings path_to_sequence path_to_association" << endl;
        return 1;
    }
  //zt6********
    const bool use_semantics = ORB_SLAM2::SemanticConfig::UseSemanticPipeline();
    int sockfd = -1;
	int len = 0;
	struct sockaddr_un address;
    int result = 0;

    if(use_semantics)
    {
        if((sockfd = socket(AF_UNIX, SOCK_STREAM, 0))==-1)//创建socket，指定通信协议为AF_UNIX,数据方式SOCK_STREAM
        {
            perror("socket");
            exit(EXIT_FAILURE);
        }
        
        //配置server_address
        address.sun_family = AF_UNIX;
        const char *socket_path_env = getenv("ORB_SLAM2_SOCKET_PATH");
        const std::string socket_path = socket_path_env ? socket_path_env : std::string("/tmp/orbslam2_semantic_socket");
        strcpy(address.sun_path, socket_path.c_str());
        len = sizeof(address);
     
        result = connect(sockfd, (struct sockaddr *)&address, len);
     
        if(result == -1) 
        {
            printf("ensure the server is up\n");
                perror("connect");
                exit(EXIT_FAILURE);
        }

        struct timeval receive_timeout;
        receive_timeout.tv_sec = 5;
        receive_timeout.tv_usec = 0;
        if(setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO,
                      &receive_timeout, sizeof(receive_timeout)) == -1)
        {
            perror("setsockopt SO_RCVTIMEO");
            exit(EXIT_FAILURE);
        }
    }
   //zt6********

    // Retrieve paths to images
    //按顺序存放需要读取的彩色图像、深度图像的路径，以及对应的时间戳的变量
    vector<string> vstrImageFilenamesRGB;
    vector<string> vstrImageFilenamesD;
    vector<double> vTimestamps;
    //从命令行输入参数中得到关联文件的路径
    string strAssociationFilename = string(argv[4]);
    //从关联文件中加载这些信息
    
strAssociationFilename = argv[4];      // 使用你传入的绝对路径 associations_abs.txt
cout << "Using association file: " << strAssociationFilename << endl;  // 输出调试信息，确认文件路径
cout << "Dataset folder: " << argv[3] << endl;    // 输出 dataset 文件夹，确认 argv[3] 是否正确


LoadImages(strAssociationFilename, vstrImageFilenamesRGB, vstrImageFilenamesD, vTimestamps);  // 真正加载图像

    // Check consistency in the number of images and depthmaps
    //彩色图像和深度图像数据的一致性检查
    int nImages = vstrImageFilenamesRGB.size();
    if(vstrImageFilenamesRGB.empty())
    {
        cerr << endl << "No images found in provided path." << endl;
        return 1;
    }
    else if(vstrImageFilenamesD.size()!=vstrImageFilenamesRGB.size())
    {
        cerr << endl << "Different number of images for rgb and depth." << endl;
        return 1;
    }

    // Create SLAM system. It initializes all system threads and gets ready to process frames.
    //初始化ORB-SLAM2系统
    ORB_SLAM2::System SLAM(argv[1],argv[2],ORB_SLAM2::System::RGBD,false);

    // Vector for tracking time statistics
    vector<float> vTimesTrack;
    vTimesTrack.resize(nImages);

    cout << endl << "-------" << endl;
    cout << "Start processing sequence ..." << endl;
    cout << "Images in the sequence: " << nImages << endl << endl;

    // Main loop
    cv::Mat imRGB, imD;
    vector<std::pair<vector<double>, int>> detect_result,detect_result_test2;
    ORB_SLAM2::ExperimentTiming::Reset(nImages, 30);
    //对图像序列中的每张图像展开遍历
    // Object obj;
    
    for(int ni=0; ni<nImages; ni++)
    {
        ORB_SLAM2::ExperimentTiming::SetCurrentFrame(ni);
        const std::chrono::steady_clock::time_point end_to_end_start =
            std::chrono::steady_clock::now();
        //****
        // string strPathToDetectionResult = argv[5] + std::to_string(vTimestamps[ni]) + ".txt";//读取detect_result
        // LoadBoundingBox(strPathToDetectionResult, detect_result);
        // if (detect_result.empty()){
        //     cerr << endl << "LoadBoundingBox is wrong !" << endl;
        //     return 1;
        // }
        //*****
        
        //! 读取图像
        // Read image and depthmap from file
        const string rgbPath = JoinDatasetPath(string(argv[3]), vstrImageFilenamesRGB[ni]);
        const string depthPath = JoinDatasetPath(string(argv[3]), vstrImageFilenamesD[ni]);
        imRGB = cv::imread(rgbPath,cv::IMREAD_UNCHANGED);
        imD = cv::imread(depthPath,cv::IMREAD_UNCHANGED);
        double tframe = vTimestamps[ni];

        //! 确定图像合法性
        if(imRGB.empty())
        {
            cerr << endl << "Failed to load image at: "
                 << rgbPath << endl;
            return 1;
        }


#ifdef COMPILEDWITHC11
        std::chrono::steady_clock::time_point t1 = std::chrono::steady_clock::now();
#else
        std::chrono::steady_clock::time_point t1 = std::chrono::steady_clock::now();
#endif

    //zt7*****
        // Pass the image to the SLAM system
        //! 追踪
        if(ni % 25 == 0)
            cout << "[RGBD_TUM] frame " << ni << "/" << nImages << endl;
        if(sockfd >= 0)
        {
            ORB_SLAM2::ScopedExperimentTimer semantic_timing(
                ORB_SLAM2::TimingComponent::SemanticDetection);
            const char send_buf[] = "ok";
            if(write(sockfd, send_buf, strlen(send_buf)) == -1)
            {
                perror("write");
                exit(EXIT_FAILURE);
            }
            MakeDetect_result(detect_result,sockfd);
        }
        else
            detect_result.clear();
        // sleep(0.5);
        {
            ORB_SLAM2::ScopedExperimentTimer tracking_timing(
                ORB_SLAM2::TimingComponent::TrackingTotal);
            SLAM.TrackRGBD(imRGB,imD,tframe,detect_result);
        }
        // ✅ 保存过滤后的彩色图像 + 特征点 + 检测框（第100帧）zt为了保存图片加入
        if (ni == 100)
        {
            cv::Mat img = imRGB.clone();

            ORB_SLAM2::Frame currentFrame = SLAM.GetTrackingFrame();  // 获取当前帧（需在 System 中添加该函数）

            // 画静态特征点
            for (size_t i = 0; i < currentFrame.mvKeys.size(); ++i)
            {
                const cv::KeyPoint& kp = currentFrame.mvKeys[i];
                if (kp.pt.x > 0 && kp.pt.y > 0)  // 被剔除的点坐标为 -100
                    cv::circle(img, kp.pt, 2, cv::Scalar(0, 255, 0), -1);  // 绿色特征点
            }

            // 画人类目标的检测框
            for (const auto& det : detect_result)
            {
                const vector<double>& bbox = det.first;
                int class_id = det.second;

                if (bbox.size() >= 4 && ORB_SLAM2::SemanticConfig::IsDynamicObjectClass(class_id))
                {
                    int left = static_cast<int>(bbox[0]);
                    int top = static_cast<int>(bbox[1]);
                    int right = static_cast<int>(bbox[2]);
                    int bottom = static_cast<int>(bbox[3]);

                    cv::rectangle(img, cv::Rect(left, top, right - left, bottom - top),
                                  cv::Scalar(255, 0, 0), 2);  // 蓝色边框
                }
            }

            // 保存图像
            const char *out_dir_env = getenv("ORB_SLAM2_OUTPUT_DIR");
            const std::string out_dir = out_dir_env ? out_dir_env : std::string("TUM_trajectory_results");
            const std::string mkdir_cmd = std::string("mkdir -p ") + out_dir;
            system(mkdir_cmd.c_str());
            cv::imwrite(out_dir + "/Frame_YDOF_filtered.png", img);
        }//zt为了保存图片加入
        detect_result.clear();
    //zt7*****  
#ifdef COMPILEDWITHC11
        std::chrono::steady_clock::time_point t2 = std::chrono::steady_clock::now();
#else
        std::chrono::steady_clock::time_point t2 = std::chrono::steady_clock::now();
#endif

        //! 计算耗时
        double ttrack= std::chrono::duration_cast<std::chrono::duration<double> >(t2 - t1).count();
        ORB_SLAM2::ExperimentTiming::Add(
            ORB_SLAM2::TimingComponent::EndToEndFrame,
            std::chrono::duration_cast<std::chrono::duration<double> >(
                t2 - end_to_end_start).count());

        vTimesTrack[ni]=ttrack;

        //! 根据时间戳,准备加载下一张图片
        // Wait to load the next frame
        double T=0;
        if(ni<nImages-1)
            T = vTimestamps[ni+1]-tframe;
        else if(ni>0)
            T = tframe-vTimestamps[ni-1];

        if(ttrack<T)
            usleep((T-ttrack)*1e6);
    }

    //终止SLAM过程
    // Stop all threads
    SLAM.Shutdown();

    // Tracking time statistics
    //统计分析追踪耗时
    sort(vTimesTrack.begin(),vTimesTrack.end());
    float totaltime = 0;
    for(int ni=0; ni<nImages; ni++)
    {
        totaltime+=vTimesTrack[ni];
    }
    cout << "-------" << endl << endl;
    cout << "median tracking time: " << vTimesTrack[nImages/2] << endl;
    cout << "mean tracking time: " << totaltime/nImages << endl;

    // Save camera trajectory
    //保存最终的相机轨迹
    //SLAM.SaveTrajectoryTUM("CameraTrajectory.txt");
    const char *out_dir_env = getenv("ORB_SLAM2_OUTPUT_DIR");
    const std::string out_dir = out_dir_env ? out_dir_env : std::string("TUM_trajectory_results");
    const std::string mkdir_cmd = std::string("mkdir -p ") + out_dir;
    system(mkdir_cmd.c_str());
    if(!ORB_SLAM2::ExperimentTiming::WriteReports(out_dir))
        cerr << "Failed to write runtime timing reports to: " << out_dir << endl;
    SLAM.SaveTrajectoryTUM(out_dir + "/CameraTrajectory.txt");
    SLAM.SaveKeyFrameTrajectoryTUM(out_dir + "/KeyFrameTrajectory.txt");
    if(ORB_SLAM2::SemanticConfig::UseObjectSemanticMap())
        SLAM.SaveSemanticObjects(out_dir + "/SemanticObjects.txt");
    SLAM.SaveSemanticDynamicStatistics(out_dir + "/SemanticDynamicStatistics.txt");

    return 0;
}

//从关联文件中提取这些需要加载的图像的路径和时间戳
void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps)
{
    //输入文件流
    ifstream fAssociation;
    //打开关联文件
    fAssociation.open(strAssociationFilename.c_str());
    //一直读取,知道文件结束
    while(!fAssociation.eof())
    {
        string s;
        //读取一行的内容到字符串s中
        getline(fAssociation,s);
        //如果不是空行就可以分析数据了
        if(!s.empty() && s[0] != '#')
        {
            //字符串流
            stringstream ss;
            ss << s;
            //字符串格式:  时间戳 rgb图像路径 时间戳 深度图像路径
            double t;
            string sRGB, sD;
            ss >> t;
            vTimestamps.push_back(t);
            ss >> sRGB;
            vstrImageFilenamesRGB.push_back(sRGB);
            ss >> t;
            ss >> sD;
            vstrImageFilenamesD.push_back(sD);

        }
    }
}
//zt8***********
void LoadBoundingBox(const string& strPathToDetectionResult, vector<std::pair<vector<double>, int>>& detect_result){
    ifstream infile;
    infile.open(strPathToDetectionResult);
    if (!infile.is_open()) {
        cout<<"yolo_detection file open fail"<<endl;
        exit(233);
    }
    vector<double> result_parameter;
    string line;
    while (getline(infile, line)){
        int sum = 0, num_bit = 0;
        for (char c : line) {//读取数字.    例如读取"748",先读7,再7*10+8=78,再78*10+4,最后读到空格结束
            if (c >= '0' && c <= '9') {
                num_bit = c - '0';
                sum = sum * 10 + num_bit;
            } else if (c == ' ') {
                result_parameter.push_back(sum);
                sum = 0;
                num_bit = 0;
            }
        }

        string idx_begin = "class:";//读取物体类别
        int idx = line.find(idx_begin);
        string idx_end = "0.";
        int idx2 = line.find(idx_end);
        string class_label;
        for (int j = idx + 6; j < idx2-1; ++j){
            class_label += line[j];
        }
        // cout << "**" << class_label << "**";

        int class_id = -1;//存入识别物体的种类
        if (class_label == "person") { //高动态物体:人,动物等
            class_id = 3;
        }

        if (class_label == "tv" ||   //低动态物体(在程序中可以假设为一直静态的物体):tv,refrigerator
            class_label == "refrigerator" || 
            class_label == "teddy bear") {
            class_id = 1;
        }

        if (class_label == "chair" || //中动态物体,在程序中不做先验动态静态判断
            class_label == "car"){
            class_id =2;
        }

        detect_result.emplace_back(result_parameter,class_id);
        result_parameter.clear();
        line.clear();
    }
    infile.close();

}

//在一句话中提取出四个边框值和物体类别,such as: left:1 top:134 right:269 bottom:478 class:person 0.79
void LoadBoundingBoxFromPython(const string& resultFromPython, std::pair<vector<double>, int>& detect_result){
    
    if(resultFromPython.empty())
    {
        cerr << "no string from python! " << endl;
    }
    // cout << "here is LoadBoundingBoxFromPython " << endl;
    vector<double> result_parameter;
    int sum = 0, num_bit = 0;

    for (char c : resultFromPython) {//读取数字.    例如读取"748",先读7,再7*10+8=78,再78*10+4,最后读到空格结束
        if (c >= '0' && c <= '9') {
            num_bit = c - '0';
            sum = sum * 10 + num_bit;
        } else if (c == ' ') {
            result_parameter.push_back(sum);
            sum = 0;
            num_bit = 0;
        }
    }

    detect_result.first = result_parameter;
    // cout << "detect_result.first size is : " << detect_result.first.size() << endl;

    string idx_begin = "class:";//读取物体类别
    int idx = resultFromPython.find(idx_begin);
    string idx_end = "0.";
    int idx2 = resultFromPython.find(idx_end);
    string class_label;
    for (int j = idx + 6; j < idx2-1; ++j){
        class_label += resultFromPython[j];
    }

    int class_id = -1;//存入识别物体的种类

    if (class_label == "tv" ||   //低动态物体(在程序中可以假设为一直静态的物体):tv,refrigerator
        class_label == "refrigerator" || 
        class_label == "teddy bear"||
        class_label == "laptop") {
        class_id = 1;
    }

    if (class_label == "chair" || //中动态物体,在程序中不做先验动态静态判断
        class_label == "car"){
        class_id =2;
    } 

    if (class_label == "person") { //高动态物体:人,动物等
        class_id = 3;
    }

    detect_result.second = class_id;
    // cout << "LoadBoundingBoxFromPython class id is: " << class_id << endl;

}

//通过UNIX的协议,从python进程中获取一帧图像的物体框
void MakeDetect_result(vector<std::pair<vector<double>, int>>& detect_result , int sockfd){
    detect_result.clear();

	std::pair<vector<double>, int> detect_result_str;
	char ch_recv[1024] = {0};

    ssize_t byte = read(sockfd, ch_recv, sizeof(ch_recv) - 1);
    if(byte==-1)
	{
		if(errno == EAGAIN || errno == EWOULDBLOCK)
			return;
		perror("read");
		exit(EXIT_FAILURE);
	}
    ch_recv[byte] = '\0';

    cout << "===== YOLO RECV =====" << endl;
    cout << ch_recv << endl;
    cout << "=====================" << endl;

    char *ptr;//char[]可读可写,可以修改字符串的内容。char*可读不可写，写入就会导致段错误
    ptr = strtok(ch_recv, "*");//字符串分割函数
    while(ptr != NULL){
        if ( strlen(ptr)>20 && strstr(ptr, "class:") != NULL){//过滤掉空白/乱码片段
            string ptr_str = ptr;
            LoadBoundingBoxFromPython(ptr_str,detect_result_str);
            detect_result.emplace_back(detect_result_str);
        } 
        // cout << "hh: " << ptr_str << endl;  
        ptr = strtok(NULL, "*");
    }
    // cout << "detect_result size is : " << detect_result.size() << endl;
    // for (int k=0; k<detect_result.size(); ++k)
        // cout << "detect_result is : \n " << detect_result[k].second << endl;


}
